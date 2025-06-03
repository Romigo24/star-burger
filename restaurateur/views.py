from collections import defaultdict
import logging

from geopy.distance import distance
from geopy.geocoders import Yandex
import requests

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from foodcartapp.models import Order, Product, Restaurant, RestaurantMenuItem


geolocator = Yandex(api_key=settings.YANDEX_GEOCODER_API_KEY, timeout=10)
GEOCODER_API_KEY = settings.YANDEX_GEOCODER_API_KEY
GEOCODER_API_URL = 'https://geocode-maps.yandex.ru/1.x'

logger = logging.getLogger(__name__)


def fetch_coordinates(api_key, address):
    url = 'https://geocode-maps.yandex.ru/1.x'
    params = {'apikey': api_key,
              'geocode': address,
              'format': 'json'}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        geo_data = response.json()
        coords = geo_data["response"]["GeoObjectCollection"]["featureMember"][0][
            "GeoObject"
        ]["Point"]["pos"]

        lon, lat = map(float, coords.split(' '))
        return lat, lon
    except (IndexError, KeyError, ValueError, requests.RequestException):
        return None, None


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {
            item.restaurant_id: item.availability for item in product.menu_items.all()
        }
        ordered_availability = [
            availability.get(restaurant.id, False) for restaurant in restaurants
        ]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = (
        Order.objects
        .with_total_price()
        .exclude(status='completed')
        .prefetch_related('items__product')
        .select_related('restaurant')
        .order_by('-status', '-id')
    )

    menu_items = RestaurantMenuItem.objects.filter(availability=True).select_related('restaurant', 'product')

    available_in = defaultdict(set)
    for item in menu_items:
        available_in[item.product_id].add(item.restaurant_id)

    restaurants = list(Restaurant.objects.all())

    for restaurant in restaurants:
        if not restaurant.lat or not restaurant.lon:
            lat, lon = fetch_coordinates(
                settings.YANDEX_GEOCODER_API_KEY, restaurant.address
            )
            if lat and lon:
                restaurant.lat = lat
                restaurant.lon = lon
                restaurant.save()

    order_infos = []

    for order in orders:
        products = [item.product for item in order.items.all()]

        if not order.lat or not order.lon:
            lat, lon = fetch_coordinates(
                settings.YANDEX_GEOCODER_API_KEY, order.address
            )
            if lat and lon:
                order.lat = lat
                order.lon = lon
                order.save()

        if order.lat and order.lon:
            order_point = (order.lat, order.lon)

        suitable_restaurants = []
        geocode_error = not (order.lat and order.lon)

        if not geocode_error:
            order_point = (order.lat, order.lon)

            for restaurant in restaurants:
                if all(restaurant.id in available_in[product.id] for product in products):
                    if restaurant.lat and restaurant.lon:
                        rest_point = (restaurant.lat, restaurant.lon)
                        dist_km = distance(order_point, rest_point).km
                        suitable_restaurants.append((restaurant, round(dist_km, 2)))
                    else:
                        geocode_error = True


            suitable_restaurants.sort(key=lambda r: r[1])
        else:
            suitable_restaurants = [
                (restaurant, None)
                for restaurant in restaurants
                if all(restaurant.id in available_in[product.id] for product in products)
            ]

        assigned_info = None
        if (
            order.restaurant
            and order.lat
            and order.lon
            and order.restaurant.lat
            and order.restaurant.lon
        ):
            rest_point = (order.restaurant.lat, order.restaurant.lon)
            assigned_distance = distance((order.lat, order.lon), rest_point).km
            assigned_info = (order.restaurant, round(assigned_distance, 2))
        elif order.restaurant:
            assigned_info = (order.restaurant, None)

        order_infos.append(
            {
                "order": order,
                "available_restaurants": suitable_restaurants,
                "assigned_restaurant_info": assigned_info,
                "geocode_error": geocode_error,
            }
        )
    return render(request, 'order_items.html', {'order_infos': order_infos})