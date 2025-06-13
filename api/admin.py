# api/admin.py - Simplified without complex features
from django.contrib import admin
from .models import Product, Store, Price

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'color_category', 'processing_status', 'created_at')
    list_filter = ('color_category', 'processing_status', 'brand')
    search_fields = ('name', 'brand', 'barcode')
    readonly_fields = ('color_category', 'color_confidence', 'processing_status', 'created_at', 'updated_at')

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name', 'address')

@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'store', 'price', 'created_at')
    list_filter = ('store', 'created_at')
    search_fields = ('product__name', 'store__name')

# Register any additional models if they exist
try:
    from .models import ProcessingJob, ColorAnalysisStats
    
    @admin.register(ProcessingJob)
    class ProcessingJobAdmin(admin.ModelAdmin):
        list_display = ('product', 'job_type', 'status', 'created_at')
        list_filter = ('job_type', 'status')
        readonly_fields = ('created_at', 'started_at', 'completed_at')
    
    @admin.register(ColorAnalysisStats)
    class ColorAnalysisStatsAdmin(admin.ModelAdmin):
        list_display = ('color_category', 'total_products', 'last_updated')
        readonly_fields = ('last_updated',)
        
except ImportError:
    # Models don't exist yet, skip registration
    pass