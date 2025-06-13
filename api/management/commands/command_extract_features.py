# api/management/commands/extract_features.py
from django.core.management.base import BaseCommand
from api import models
from api.models import Product
from api.util import extract_visual_features, get_text_embedding, build_vector_index
import urllib.request
import io

class Command(BaseCommand):
    help = 'Existing ürünler için görsel ve metin özelliklerini çıkar'

    def handle(self, *args, **options):
        products = Product.objects.filter(
            models.Q(visual_embedding__isnull=True) | 
            models.Q(text_embedding__isnull=True)
        )
        
        count = 0
        errors = 0
        
        for product in products:
            try:
                # Metin embedding'i yoksa oluştur
                if not product.text_embedding:
                    text_embedding = get_text_embedding(product.name)
                    product.text_embedding = text_embedding.tolist()
                
                # Görsel embedding'i yoksa ve görsel URL'si varsa oluştur
                if not product.visual_embedding and product.image_url:
                    try:
                        # URL'den görüntü indir
                        img_data = urllib.request.urlopen(product.image_url).read()
                        img = io.BytesIO(img_data)
                        
                        # Görsel özellikler
                        visual_features = extract_visual_features(img)
                        product.visual_embedding = visual_features.tolist()
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Görüntü indirme hatası ({product.name}): {e}"))
                        errors += 1
                        continue
                
                product.save()
                count += 1
                self.stdout.write(self.style.SUCCESS(f"İşlendi: {product.name}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata ({product.name}): {e}"))
                errors += 1
        
        # FAISS indeksini yeniden oluştur
        build_vector_index()
        
        self.stdout.write(self.style.SUCCESS(f"Tamamlandı: {count} ürün işlendi, {errors} hata"))