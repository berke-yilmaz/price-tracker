# api/management/commands/visual_search_enhanced.py
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Product
from api.util import (
    extract_visual_features_resnet, 
    get_enhanced_vector_index, 
    safe_remove_background,
    categorize_by_color
)
import os
import argparse
from PIL import Image
import time

class Command(BaseCommand):
    help = 'Enhanced visual search with color awareness'

    def add_arguments(self, parser):
        parser.add_argument('image_path', type=str, help='Aranacak görselin dosya yolu')
        parser.add_argument('--remove-bg', action='store_true', help='Arka planı kaldır')
        parser.add_argument('--top-k', type=int, default=5, help='Gösterilecek sonuç sayısı')
        parser.add_argument('--detail', action='store_true', help='Detaylı bilgileri göster')
        parser.add_argument('--threshold', type=float, default=0.0, help='Benzerlik eşiği (0-1 arası)')
        parser.add_argument('--color-filter', type=str, 
                           choices=['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'white', 'black', 'brown', 'pink'],
                           help='Belirli renk kategorisinde ara')
        parser.add_argument('--analyze-query-color', action='store_true', 
                           help='Sorgu görselinin rengini analiz et ve ona göre ara')
        parser.add_argument('--include-similar-colors', action='store_true', default=True,
                           help='Benzer renklerde de ara')

    def handle(self, *args, **options):
        image_path = options['image_path']
        remove_bg = options['remove_bg']
        top_k = options['top_k']
        detail = options['detail']
        threshold = options['threshold']
        color_filter = options['color_filter']
        analyze_query_color = options['analyze_query_color']
        include_similar_colors = options['include_similar_colors']
        
        if not os.path.exists(image_path):
            self.stdout.write(self.style.ERROR(f"Dosya bulunamadı: {image_path}"))
            return
        
        # Load enhanced FAISS index
        try:
            vector_index = get_enhanced_vector_index()
            total_products = sum(idx['index'].ntotal for idx in vector_index.color_indices.values())
            self.stdout.write(self.style.SUCCESS(f"Enhanced indeks yüklendi ({total_products} ürün)"))
            
            # Show color distribution in index
            if detail:
                self.stdout.write("\nİndeksteki renk dağılımı:")
                for color, color_index in vector_index.color_indices.items():
                    count = color_index['index'].ntotal
                    if count > 0:
                        color_display = dict(Product.COLOR_CHOICES).get(color, color)
                        self.stdout.write(f"  {color_display}: {count} ürün")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"İndeks hatası: {e}"))
            return
        
        # Load and process image
        try:
            self.stdout.write("Görsel işleniyor...")
            start_time = time.time()
            
            # Load image
            img = Image.open(image_path).convert('RGB')
            self.stdout.write(f"Görsel yüklendi: {img.size[0]}x{img.size[1]}")
            
            # Analyze color if requested
            query_color = color_filter
            if analyze_query_color or not color_filter:
                self.stdout.write("Görsel renk analizi yapılıyor...")
                color_info = categorize_by_color(img)
                detected_color = color_info['category']
                confidence = color_info['confidence']
                
                self.stdout.write(f"Tespit edilen renk: {dict(Product.COLOR_CHOICES).get(detected_color, detected_color)} (güven: {confidence:.2f})")
                
                if not color_filter:
                    query_color = detected_color
                    self.stdout.write(f"Arama rengi olarak '{dict(Product.COLOR_CHOICES).get(detected_color, detected_color)}' kullanılacak")
            
            # Process image for feature extraction
            if remove_bg:
                self.stdout.write("Arka plan kaldırılıyor...")
                try:
                    processed_img, bg_success = safe_remove_background(img, fallback_to_original=True)
                    if bg_success:
                        self.stdout.write("Arka plan başarıyla kaldırıldı")
                        visual_features = extract_visual_features_resnet(processed_img, remove_bg=False, color_category=query_color)
                    else:
                        self.stdout.write(self.style.WARNING("Arka plan kaldırma başarısız, orijinal görsel kullanılıyor"))
                        visual_features = extract_visual_features_resnet(img, remove_bg=False, color_category=query_color)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Arka plan kaldırma hatası: {e}"))
                    visual_features = extract_visual_features_resnet(img, remove_bg=False, color_category=query_color)
            else:
                visual_features = extract_visual_features_resnet(img, remove_bg=False, color_category=query_color)
            
            process_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f"Görsel işlendi ({process_time:.2f} sn) - ResNet50 özellikler: {len(visual_features)} boyut"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Görsel işleme hatası: {e}"))
            return
        
        # Search for similar products
        self.stdout.write("Color-aware benzer ürünler aranıyor...")
        search_start = time.time()
        
        results = vector_index.search(
            visual_features, 
            color_category=query_color,
            k=top_k,
            search_similar_colors=include_similar_colors
        )
        
        search_time = time.time() - search_start
        
        # Display results
        self.stdout.write(self.style.SUCCESS(f"Arama tamamlandı! ({search_time:.4f} sn)"))
        
        if query_color:
            query_color_display = dict(Product.COLOR_CHOICES).get(query_color, query_color)
            self.stdout.write(f"Arama kriteri: {query_color_display} renk kategorisi")
            if include_similar_colors:
                self.stdout.write("(Benzer renkler de dahil)")
        
        self.stdout.write(f"\nEn benzer {len(results)} ürün:")
        
        if not results:
            self.stdout.write(self.style.WARNING("Benzer ürün bulunamadı!"))
            return
        
        for i, result in enumerate(results):
            product_id = result['product_id']
            distance = result['distance']
            similarity = 1.0 - min(distance / 100.0, 1.0)  # Normalize (0-1 arası)
            is_exact_color_match = result.get('is_exact_color_match', False)
            
            # Apply threshold
            if similarity < threshold:
                continue
                
            try:
                product = Product.objects.get(id=product_id)
                
                # Color match indicator
                color_indicator = "🎯" if is_exact_color_match else "🔍"
                product_color = dict(Product.COLOR_CHOICES).get(product.color_category, product.color_category)
                
                self.stdout.write(f"\n{i+1}. {color_indicator} {product.name} ({product.brand})")
                self.stdout.write(f"   Benzerlik: {similarity:.4f} (mesafe: {distance:.2f})")
                self.stdout.write(f"   Renk: {product_color} (güven: {product.color_confidence:.2f})")
                
                if is_exact_color_match:
                    self.stdout.write(f"   ✅ Tam renk eşleşmesi!")
                
                if detail:
                    self.stdout.write(f"   Kategori: {product.category}")
                    self.stdout.write(f"   Barkod: {product.barcode}")
                    self.stdout.write(f"   ID: {product.id}")
                    self.stdout.write(f"   URL: {product.image_url}")
                    self.stdout.write(f"   İşleme durumu: {product.get_processing_status_display()}")
                    
                    if product.dominant_colors:
                        self.stdout.write(f"   Dominant renkler: {len(product.dominant_colors)} renk tespit edildi")
                    
                    # Price information
                    prices = product.prices.all().order_by('price')[:3]
                    if prices:
                        self.stdout.write("   En düşük fiyatlar:")
                        for price in prices:
                            self.stdout.write(f"     - {price.price} TL ({price.store.name}) - {price.created_at.strftime('%d.%m.%Y')}")
                    else:
                        self.stdout.write("   Henüz fiyat bilgisi yok")
                        
            except Product.DoesNotExist:
                self.stdout.write(f"{i+1}. ❌ Ürün bulunamadı (ID: {product_id})")
        
        # Show search statistics
        self.stdout.write(f"\n📊 Arama İstatistikleri:")
        exact_matches = sum(1 for r in results if r.get('is_exact_color_match', False))
        self.stdout.write(f"   Tam renk eşleşmesi: {exact_matches}/{len(results)}")
        self.stdout.write(f"   Ortalama benzerlik: {sum(1.0 - min(r['distance']/100.0, 1.0) for r in results)/len(results):.3f}")
        
        if query_color and query_color != 'unknown':
            color_matches = sum(1 for r in results if r.get('is_exact_color_match', False))
            self.stdout.write(f"   {dict(Product.COLOR_CHOICES).get(query_color, query_color)} kategorisinde: {color_matches} eşleşme")