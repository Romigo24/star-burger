# Generated by Django 4.2 on 2025-05-31 21:47

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0046_order_payment_alter_order_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='restaurant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='foodcartapp.restaurant', verbose_name='Ресторан'),
        ),
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(db_index=True, default=datetime.datetime(2025, 5, 31, 21, 47, 57, 937294, tzinfo=datetime.timezone.utc), verbose_name='Дата создания'),
        ),
    ]
