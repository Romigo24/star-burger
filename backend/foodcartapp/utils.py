from django.conf import settings
import logging
import requests
from django.db import transaction

from geopy.geocoders import Yandex

from .models import Place


geolocator = Yandex(api_key=settings.YANDEX_GEOCODER_API_KEY, timeout=10)
GEOCODER_API_KEY = settings.YANDEX_GEOCODER_API_KEY
GEOCODER_API_URL = 'https://geocode-maps.yandex.ru/1.x'

logger = logging.getLogger(__name__)


def fetch_coordinates(api_key, address, max_retries=3):
    url = 'https://geocode-maps.yandex.ru/1.x'
    params = {
        'apikey': api_key,
        'geocode': address,
        'format': 'json'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            geo_data = response.json()
            features = geo_data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
            
            if not features:
                logger.debug(f"Не найдены координаты для адреса: {address}")
                return None, None
                
            coords = features[0]["GeoObject"]["Point"]["pos"]
            lon, lat = map(float, coords.split(' '))
            return lat, lon
            
        except requests.Timeout:
            if attempt == max_retries - 1:
                logger.warning(f"Таймаут геокодирования для адреса: {address}")
                return None, None
        except Exception as e:
            logger.error(f"Ошибка геокодирования (попытка {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                return None, None


def create_or_update_location(address, obj=None):
    if not address:
        logger.error("Передан пустой адрес")
        return None
    
    try:
        with transaction.atomic():
            place, created = Place.objects.get_or_create(address=address)
            
            if created or not (place.lat and place.lon):
                lat, lon = fetch_coordinates(settings.YANDEX_GEOCODER_API_KEY, address)
                if lat and lon:
                    place.lat = lat
                    place.lon = lon
                    place.save(update_fields=['lat', 'lon'])
            
            if obj and hasattr(obj, 'location'):
                obj.location = place
                obj.save(update_fields=['location'])
            
            return place
            
    except Exception as e:
        logger.error(f"Ошибка при обработке локации для {address}: {str(e)}")
        return None