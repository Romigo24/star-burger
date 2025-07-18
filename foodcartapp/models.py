from django.db import models
from django.db.models import Sum, F, DecimalField
from django.core.validators import MinValueValidator
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class OrderQuerySet(models.QuerySet):
    def with_total_price(self):
        return self.annotate(
            total_price=Sum(
                F('items__price') * F('items__quantity'),
                output_field=DecimalField()
            )
        )

class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )
    location = models.ForeignKey(
        'Place',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='координаты',
        related_name='restaurants'
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('unprocessed', 'Необработанный'),
        ('confirmed', 'Подтверждённый'),
        ('assembled', 'Собран'),
        ('delivering', 'В доставке'),
        ('completed', 'Завершён'),
    ]

    PAYMENT_CHOICES = [
        ('cash', 'Наличностью'),
        ('card', 'Электронно')
    ]
    
    firstname = models.CharField('Имя', max_length=30)
    lastname = models.CharField('Фамилия', max_length=30)
    phonenumber = PhoneNumberField('Номер телефона', db_index=True)
    address = models.CharField('Адрес доставки', max_length=255)
    objects = OrderQuerySet.as_manager()
    status = models.CharField(
        'статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='unprocessed',
        db_index=True
    )

    comment = models.TextField('Комментарий', blank=True)
    created_at = models.DateTimeField(
        'Дата создания',
        default=timezone.now,
        db_index=True,
    )

    called_at = models.DateTimeField(
        'Время звонка клиенту',
        blank=True,
        null=True,
        db_index=True,
    )

    delivered_at = models.DateTimeField(
        'Время доставки',
        blank=True,
        null=True,
        db_index=True,
    )

    payment = models.CharField(
        'Способ оплаты',
        max_length=20,
        choices=PAYMENT_CHOICES,
        default='cash',
        db_index=True
    )

    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='Ресторан',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    location = models.ForeignKey(
        'Place',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='координаты',
        related_name='orders'
    )


    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def save(self, *args, **kwargs):
        if self.restaurant and self.status == 'unprocessed':
            self.status = 'confirmed'
            if not self.called_at:
                self.called_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.firstname} {self.lastname} - {self.address}'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='товар',
    )
    quantity = models.PositiveBigIntegerField(
        'количество',
        validators=[MinValueValidator(1)],
    )

    price = models.DecimalField(
        'цена за единицу',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name='позиция заказа'
        verbose_name_plural = 'позиции заказа'

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)


class Place(models.Model):
    address = models.CharField('адрес', max_length=255, unique=True)
    lat = models.FloatField('широта', blank=True, null=True)
    lon = models.FloatField('долгота', blank=True, null=True)

    class Meta:
        verbose_name = 'координаты'
        verbose_name_plural = 'координаты'

    def __str__(self):
        return self.address