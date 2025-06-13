# api/models.py - Enhanced with Color Categorization
from datetime import timezone
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField  # This is the correct import for ArrayField
from django.utils.timezone import now as timezone_now
from django.utils import timezone
import datetime
import numpy as np


class Product(models.Model):
    # Basic product information
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100, blank=True) 
    image_url = models.URLField(blank=True)
    image_front_url = models.URLField(blank=True)
    weight = models.CharField(max_length=50, blank=True)
    ingredients = models.TextField(blank=True)
    
    # Enhanced color categorization fields
    COLOR_CHOICES = [
        ('red', 'Kırmızı'),
        ('orange', 'Turuncu'),
        ('yellow', 'Sarı'),
        ('green', 'Yeşil'),
        ('blue', 'Mavi'),
        ('purple', 'Mor'),
        ('white', 'Beyaz'),
        ('black', 'Siyah'),
        ('brown', 'Kahverengi'),
        ('pink', 'Pembe'),
        ('unknown', 'Belirsiz'),
    ]
    
    color_category = models.CharField(
        max_length=20, 
        choices=COLOR_CHOICES, 
        default='unknown',
        db_index=True,  # Index for fast color-based queries
        help_text="Ürünün dominant renk kategorisi"
    )
    
    color_confidence = models.FloatField(
        default=0.0,
        help_text="Renk kategorizasyonunun güven skoru (0-1 arası)"
    )
    
    dominant_colors = ArrayField(
        ArrayField(models.IntegerField(), size=3),  # RGB values
        blank=True,
        null=True,
        help_text="Ürünün dominant renkleri (RGB formatında)"
    )
    
    # Enhanced vector embeddings (ResNet50 - 2048 dimensional)
    visual_embedding = ArrayField(
        models.FloatField(), 
        blank=True, 
        null=True,
        help_text="ResNet50 ile çıkarılan görsel özellik vektörü (2048 boyut)"
    )
    
    text_embedding = ArrayField(
        models.FloatField(), 
        blank=True, 
        null=True,
        help_text="Metin embedding vektörü"
    )
    
    # Color-aware text embedding (includes color context)
    color_aware_text_embedding = ArrayField(
        models.FloatField(),
        blank=True,
        null=True,
        help_text="Renk bilgisi ile zenginleştirilmiş metin embedding"
    )
    
    # Processing metadata
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Beklemede'),
            ('processing', 'İşleniyor'), 
            ('completed', 'Tamamlandı'),
            ('failed', 'Başarısız'),
        ],
        default='pending',
        help_text="Görsel işleme durumu"
    )
    
    processing_error = models.TextField(
        blank=True,
        null=True,
        help_text="İşleme sırasında oluşan hata mesajı"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Görsel işlemenin tamamlandığı zaman"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['color_category']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['brand', 'color_category']),
            models.Index(fields=['category', 'color_category']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        color_display = dict(self.COLOR_CHOICES).get(self.color_category, 'Belirsiz')
        return f"{self.name} ({color_display})"
    
    @property
    def has_visual_features(self):
        """Check if product has visual embeddings"""
        return self.visual_embedding is not None and len(self.visual_embedding) > 0
    
    @property
    def has_color_analysis(self):
        """Check if product has color analysis"""
        return self.color_category != 'unknown' and self.color_confidence > 0
    
    @property
    def is_processed(self):
        """Check if product processing is complete"""
        return self.processing_status == 'completed'
    
    def get_color_display(self):
        """Get Turkish display name for color"""
        return dict(self.COLOR_CHOICES).get(self.color_category, 'Belirsiz')

class Store(models.Model):
    name = models.CharField(max_length=100)
    
    # Geographic location
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # User who recorded the price
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField(default=datetime.date.today)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'store', 'date'], 
                name='unique_daily_price'
            )
        ]
        indexes = [
            models.Index(fields=['product', 'date']),
            models.Index(fields=['store', 'date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.price}₺ ({self.store.name})"

# New model for color analysis statistics
class ColorAnalysisStats(models.Model):
    """Store color analysis statistics for monitoring and optimization"""
    
    color_category = models.CharField(max_length=20, choices=Product.COLOR_CHOICES)
    total_products = models.IntegerField(default=0)
    avg_confidence = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Performance metrics
    avg_processing_time = models.FloatField(
        default=0.0,
        help_text="Ortalama işleme süresi (saniye)"
    )
    success_rate = models.FloatField(
        default=0.0,
        help_text="Başarı oranı (0-1 arası)"
    )
    
    class Meta:
        unique_together = ['color_category']
        verbose_name = "Color Analysis Statistics"
        verbose_name_plural = "Color Analysis Statistics"
    
    def __str__(self):
        return f"{self.get_color_category_display()}: {self.total_products} products"

# New model for storing processing jobs

# api/models.py - Updated ProcessingJob model

class ProcessingJob(models.Model):
    """Track background processing jobs for products"""
    
    JOB_TYPES = [
        ('color_analysis', 'Renk Analizi'),
        ('visual_features', 'Görsel Özellik Çıkarma'),
        ('text_embedding', 'Metin Embedding'),
        ('background_removal', 'Arka Plan Kaldırma'),
        ('enhanced_processing', 'Gelişmiş İşleme'),
        ('enhanced_color_analysis', 'Gelişmiş Renk Analizi'),
        ('standard_processing', 'Standart İşleme'),
    ]
    
    STATUS_CHOICES = [
        ('queued', 'Sırada'),
        ('running', 'Çalışıyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='processing_jobs'
    )
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)  # INCREASED FROM 20 TO 50
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results and errors
    result_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Priority and retry logic
    priority = models.IntegerField(default=0, help_text="Yüksek sayı = yüksek öncelik")
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['product', 'job_type']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.get_job_type_display()} ({self.status})"
    
    @property
    def processing_time(self):
        """Calculate processing time if job is completed"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def can_retry(self):
        """Check if job can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries
    """Track background processing jobs for products"""
    
    JOB_TYPES = [
        ('color_analysis', 'Renk Analizi'),
        ('visual_features', 'Görsel Özellik Çıkarma'),
        ('text_embedding', 'Metin Embedding'),
        ('background_removal', 'Arka Plan Kaldırma'),
    ]
    
    STATUS_CHOICES = [
        ('queued', 'Sırada'),
        ('running', 'Çalışıyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='processing_jobs'
    )
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results and errors
    result_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Priority and retry logic
    priority = models.IntegerField(default=0, help_text="Yüksek sayı = yüksek öncelik")
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['product', 'job_type']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.get_job_type_display()} ({self.status})"
    
    @property
    def processing_time(self):
        """Calculate processing time if job is completed"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def can_retry(self):
        """Check if job can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries