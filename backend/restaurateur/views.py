from collections import defaultdict
import logging

from geopy.distance import distance

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from foodcartapp.models import Order, Product, Restaurant, RestaurantMenuItem


logger = logging.getLogger(__name__)


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


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_orders(request):
    orders = (
        Order.objects
        .with_total_price()
        .exclude(status='completed')
        .prefetch_related('items__product')
        .select_related('restaurant', 'location')
        .order_by('-status', '-id')
    )

    restaurants = list(Restaurant.objects.select_related('location'))
    menu_items = RestaurantMenuItem.objects.filter(
        availability=True
    ).select_related("restaurant", "product")

    available_in = defaultdict(set)
    for item in menu_items:
        available_in[item.product_id].add(item.restaurant_id)

    restaurants_to_update = []
    restaurant_coords = {}

    for restaurant in restaurants:
        if restaurant.location.lat and restaurant.location.lon:
            restaurant_coords[restaurant.id] = (restaurant.location.lat, restaurant.location.lon)
        else:
            restaurant_coords[restaurant.id] = (None, None)

    if restaurants_to_update:
        Restaurant.objects.bulk_update(restaurants_to_update, ['location'])

    orders_to_update = []
    order_coords = {}

    for order in orders:
            if order.location.lat and order.location.lon:
                order_coords[order.id] = (order.location.lat, order.location.lon)
            else:
                order_coords[order.id] = (None, None)

    if orders_to_update:
        Order.objects.bulk_update(orders_to_update, ['location'])

    order_infos = []

    for order in orders:
        products = [item.product for item in order.items.all()]
        order_point = order_coords.get(order.id)
        geocode_error = order_point is None

        suitable_restaurants = []
        if order_point:
            for restaurant in restaurants:
                if all(restaurant.id in available_in[product.id] for product in products):
                    rest_point = restaurant_coords.get(restaurant.id)
                    if rest_point:
                        dist = distance(order_point, rest_point).km
                        suitable_restaurants.append((restaurant, round(dist, 2)))
            suitable_restaurants.sort(key=lambda r: r[1])

        assigned_info = None
        if order.restaurant:
            rest_point = restaurant_coords.get(order.restaurant.id)
            if order_point and rest_point:
                assigned_info = (
                    order.restaurant,
                    round(distance(order_point, rest_point).km, 2)
                )
            else:
                assigned_info = (order.restaurant, None)

        order_infos.append({
            "order": order,
            "available_restaurants": suitable_restaurants,
            "assigned_restaurant_info": assigned_info,
            "geocode_error": geocode_error,
        })

    return render(request, "order_items.html", {"order_infos": order_infos})