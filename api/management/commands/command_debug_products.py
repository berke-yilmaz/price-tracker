# api/management/commands/debug_products.py
from django.core.management.base import BaseCommand
from django.db import models

from api.models import Product
from api.util import get_enhanced_vector_index, extract_visual_features, get_text_embedding
import urllib.request
import io

class Command(BaseCommand):
    help = 'Ürün ve indeks durumunu kontrol et'

    def handle(self, *args, **options):
        # Ürün sayıları
        total_products = Product.objects.count()
        products_with_visual = Product.objects.filter(visual_embedding__isnull=False).count()
        products_with_text = Product.objects.filter(text_embedding__isnull=False).count()
        products_with_image = Product.objects.exclude(image_url='').count()
        
        self.stdout.write(f"Toplam ürün: {total_products}")
        self.stdout.write(f"Görsel özelliği olan: {products_with_visual}")
        self.stdout.write(f"Metin özelliği olan: {products_with_text}")
        self.stdout.write(f"Görsel URL'si olan: {products_with_image}")
        
        # Enhanced FAISS indeks durumu
        try:
            enhanced_index = get_enhanced_vector_index()
            
            # Calculate total indexed products across all color categories
            total_indexed = 0
            color_breakdown = {}
            
            for color, color_data in enhanced_index.color_indices.items():
                count = color_data['index'].ntotal
                if count > 0:
                    color_breakdown[color] = count
                    total_indexed += count
            
            self.stdout.write(f"Enhanced FAISS indeks toplam: {total_indexed} ürün")
            
            if color_breakdown:
                self.stdout.write("Renk kategorilerine göre dağılım:")
                for color, count in sorted(color_breakdown.items(), key=lambda x: x[1], reverse=True):
                    # Get Turkish color name
                    color_display = dict(Product.COLOR_CHOICES).get(color, color)
                    self.stdout.write(f"  {color_display}: {count} ürün")
            else:
                self.stdout.write("Henüz hiçbir ürün indekslenmemiş")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Enhanced FAISS indeks hatası: {e}"))
        
        # Color category distribution in database
        if total_products > 0:
            self.stdout.write("\nVeritabanındaki renk dağılımı:")
            color_stats = Product.objects.values('color_category').annotate(
                count=models.Count('id')
            ).order_by('-count')
            
            for stat in color_stats:
                color = stat['color_category']
                count = stat['count']
                color_display = dict(Product.COLOR_CHOICES).get(color, color)
                percentage = (count / total_products) * 100
                self.stdout.write(f"  {color_display}: {count} ürün ({percentage:.1f}%)")
        
        # Processing status
        if total_products > 0:
            processing_stats = Product.objects.values('processing_status').annotate(
                count=models.Count('id')
            ).order_by('-count')
            
            self.stdout.write("\nİşleme durumu:")
            for stat in processing_stats:
                status = stat['processing_status']
                count = stat['count']
                self.stdout.write(f"  {status}: {count} ürün")
        
        # Örnek ürün test et (sadece görsel özelliği olmayan varsa)
        test_product = Product.objects.filter(
            visual_embedding__isnull=True, 
            image_url__isnull=False
        ).exclude(image_url='').first()
        
        if test_product:
            self.stdout.write(f"\nTest ürünü: {test_product.name}")
            try:
                req = urllib.request.Request(
                    test_product.image_url,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    img_data = response.read()
                    img = io.BytesIO(img_data)
                    features = extract_visual_features(img)
                    self.stdout.write(f"Görsel özellik boyutu: {features.shape}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Test hatası: {e}"))
        else:
            if total_products > 0:
                self.stdout.write("\nTüm ürünlerin görsel özellikleri mevcut ✅")
            else:
                self.stdout.write("\nTest edilecek ürün yok")