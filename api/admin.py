from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Product, Store, Price

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'barcode')
    search_fields = ('name', 'brand', 'barcode')
    list_filter = ('category', 'brand')

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name', 'address')

@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'store', 'price', 'created_at')
    list_filter = ('store', 'created_at')
    search_fields = ('product__name', 'store__name')
    date_hierarchy = 'created_at'