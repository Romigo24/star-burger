from django.http import JsonResponse
from django.templatetags.static import static
from django.db import transaction
from .serializers import OrderSerializer


from .models import Product, Order, OrderItem
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


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

@transaction.atomic
@api_view(['POST'])
def register_order(request):
    serializer = OrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    products = serializer.validated_data['products']
    firstname = serializer.validated_data['firstname']
    lastname = serializer.validated_data['lastname']
    phonenumber = serializer.validated_data['phonenumber']
    address = serializer.validated_data['address']

    order = Order.objects.create(
        firstname=firstname,
        lastname=lastname,
        phonenumber=phonenumber,
        address=address,
    )

    for product in products:
        OrderItem.objects.create(
            order=order,
            product=product['product'],
            quantity=product['quantity'],
            price=product['product'].price
        )

    order_serializer = OrderSerializer(order)

    return Response(order_serializer.data, status=status.HTTP_201_CREATED)