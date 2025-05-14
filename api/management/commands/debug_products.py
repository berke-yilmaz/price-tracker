# api/management/commands/debug_products.py
from django.core.management.base import BaseCommand
from api.models import Product
from api.util import get_vector_index, extract_visual_features, get_text_embedding
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
        
        # FAISS indeks durumu
        try:
            index = get_vector_index()
            self.stdout.write(f"FAISS indeks boyutu: {index.index.ntotal}")
            self.stdout.write(f"İndekslenen ürün: {len(index.product_ids)}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FAISS indeks hatası: {e}"))
        
        # Örnek ürün test et
        test_product = Product.objects.filter(visual_embedding__isnull=True, image_url__isnull=False).first()
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