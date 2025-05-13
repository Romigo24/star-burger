import json
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Product, Order, OrderItem


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@api_view(['POST'])
def register_order(request):
    new_order = request.data
    print('Новый заказ через DRF:', new_order)

    products = new_order.get('products', None)

    if products is None:
        message = "Обязательное поле."
    elif not isinstance(products, list):
        message = "Ожидался list со значениями, но был получен другой тип."
    elif len(products) == 0:
        message = "Этот список не может быть пустым."
    else:
        message = None

    if message:
        return Response(
            {"products": message},
            status=status.HTTP_400_BAD_REQUEST
        )

    order = Order.objects.create(
        first_name=new_order['firstname'],
        last_name=new_order.get('lastname', ''),
        phone_number=new_order['phonenumber'],
        address=new_order['address']
    )

    for item in new_order['products']:
        product = Product.objects.get(pk=item['product'])
        OrderItem.objects.create(
            order=order,
            product=product,
            quanity=item['quantity'],
        )
    return Response({'status': 'ok'})