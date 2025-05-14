from datetime import timezone
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.utils.timezone import now as timezone_now
from django.utils import timezone
import datetime

class Product(models.Model):
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100, blank=True) 
    image_url = models.URLField(blank=True)
    image_front_url = models.URLField(blank=True)
    weight = models.CharField(max_length=50, blank=True)
    ingredients = models.TextField(blank=True)
    
    # Vektör alanları (pgvector kullanılıyorsa)
    visual_embedding = ArrayField(models.FloatField(), blank=True, null=True)
    text_embedding = ArrayField(models.FloatField(), blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Store(models.Model):
    name = models.CharField(max_length=100)
    
    # Coğrafi konum
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    address = models.TextField(blank=True)


class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Kaydeden kullanıcı
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Zaman damgası
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField(default=datetime.date.today)  # Use datetime.date.today without parentheses
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'store', 'date'], 
                name='unique_daily_price'
            )
        ]