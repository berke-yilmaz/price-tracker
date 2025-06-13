# api/management/commands/complete_features.py
from django.core.management.base import BaseCommand
from django.db import models
from api.models import Product
from api.util import extract_visual_features, get_text_embedding, build_vector_index
import urllib.request
import io

class Command(BaseCommand):
    help = 'Eksik görsel ve metin özelliklerini tamamla'

    def add_arguments(self, parser):
        parser.add_argument('--visual-only', action='store_true', help='Sadece görsel özellikleri tamamla')
        parser.add_argument('--text-only', action='store_true', help='Sadece metin özellikleri tamamla')

    def handle(self, *args, **options):
        visual_only = options['visual_only']
        text_only = options['text_only']
        
        if not visual_only and not text_only:
            # Her ikisini de yap
            visual_only = text_only = True
        
        count = 0
        
        # Eksik görsel özellikler
        if visual_only:
            products_without_visual = Product.objects.filter(
                models.Q(visual_embedding__isnull=True) & ~models.Q(image_url='')
            )
            
            self.stdout.write(f"Görsel özelliği eksik {products_without_visual.count()} ürün bulundu")
            
            for product in products_without_visual:
                try:
                    req = urllib.request.Request(
                        product.image_url,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        img_data = response.read()
                        img = io.BytesIO(img_data)
                        
                        visual_features = extract_visual_features(img)
                        product.visual_embedding = visual_features.tolist()
                        product.save()
                        
                        count += 1
                        self.stdout.write(f"✓ {product.name}")
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ {product.name}: {e}"))
        
        # Eksik metin özellikler
        if text_only:
            products_without_text = Product.objects.filter(text_embedding__isnull=True)
            
            self.stdout.write(f"Metin özelliği eksik {products_without_text.count()} ürün bulundu")
            
            for product in products_without_text:
                try:
                    text_embedding = get_text_embedding(product.name)
                    product.text_embedding = text_embedding.tolist()
                    product.save()
                    
                    count += 1
                    self.stdout.write(f"✓ {product.name}")
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ {product.name}: {e}"))
        
        # Indeksi yeniden oluştur
        if count > 0:
            self.stdout.write("\nIndeks yeniden oluşturuluyor...")
            build_vector_index()
            self.stdout.write(self.style.SUCCESS(f"{count} ürün işlendi, indeks güncellendi"))