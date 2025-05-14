#!/usr/bin/env python3
# api/management/commands/cleanup_products.py
from django.core.management.base import BaseCommand
from api.models import Product
import pandas as pd
import numpy as np
from django.db.models import Count, F, Q
from fuzzywuzzy import fuzz
from django.db import transaction
import logging

class Command(BaseCommand):
    help = 'Veritabanındaki ürünleri temizleme ve düzenleme'

    def add_arguments(self, parser):
        parser.add_argument('--list-only', action='store_true', help='Sadece sorunlu ürünleri listele, silme')
        parser.add_argument('--duplicates', action='store_true', help='Aynı isimli veya benzer ürünleri bul')
        parser.add_argument('--incomplete', action='store_true', help='Eksik bilgileri olan ürünleri bul')
        parser.add_argument('--no-visuals', action='store_true', help='Görsel özelliği olmayan ürünleri bul')
        parser.add_argument('--no-text', action='store_true', help='Metin özelliği olmayan ürünleri bul')
        parser.add_argument('--no-brand', action='store_true', help='Markası olmayan ürünleri bul')
        parser.add_argument('--category', type=str, help='Belirli bir kategorideki ürünleri temizle')
        parser.add_argument('--auto-clean', action='store_true', help='Otomatik temizlik yap')
        parser.add_argument('--similarity', type=int, default=90, help='Benzerlik eşiği (0-100 arası)')
        parser.add_argument('--delete', action='store_true', help='Sorunlu ürünleri sil')
        parser.add_argument('--merge', action='store_true', help='Benzer ürünleri birleştir')
        parser.add_argument('--limit', type=int, default=0, help='Maksimum işlenecek ürün sayısı (0=tümü)')

    def handle(self, *args, **options):
        list_only = options['list_only']
        find_duplicates = options['duplicates']
        find_incomplete = options['incomplete']
        find_no_visuals = options['no_visuals']
        find_no_text = options['no_text']
        find_no_brand = options['no_brand']
        category = options['category']
        auto_clean = options['auto_clean']
        similarity_threshold = options['similarity']
        do_delete = options['delete']
        do_merge = options['merge']
        limit = options['limit']
        
        # Varsayılan olarak, hiçbir seçenek belirtilmezse, tüm kontrolleri yap
        if not any([find_duplicates, find_incomplete, find_no_visuals, find_no_text, find_no_brand]):
            find_duplicates = find_incomplete = find_no_visuals = find_no_text = find_no_brand = True
        
        # Kategori filtresi
        base_query = Product.objects.all()
        if category:
            base_query = base_query.filter(category=category)
            self.stdout.write(f"'{category}' kategorisindeki ürünler işlenecek...")
        
        # Limit uygula
        if limit > 0:
            base_query = base_query[:limit]
            
        total_products = base_query.count()
        self.stdout.write(f"Toplam {total_products} ürün incelenecek")
        
        # 1. Markası olmayan ürünleri bul
        if find_no_brand:
            no_brand_products = base_query.filter(Q(brand='') | Q(brand__isnull=True))
            self.stdout.write(self.style.WARNING(f"\n{no_brand_products.count()} ürünün markası yok:"))
            
            for product in no_brand_products:
                self.stdout.write(f"ID: {product.id}, Ad: {product.name}")
                
                # Otomatik temizlik veya silme
                if auto_clean and not list_only:
                    # Markanın muhtemelen name içinde olduğunu varsayalım
                    name_parts = product.name.split()
                    if len(name_parts) > 1 and len(name_parts[0]) > 2:
                        product.brand = name_parts[0]
                        product.save()
                        self.stdout.write(self.style.SUCCESS(f"  -> Marka otomatik ayarlandı: {product.brand}"))
                elif do_delete and not list_only:
                    product.delete()
                    self.stdout.write(self.style.SUCCESS(f"  -> Silindi"))
                
        # 2. Görsel embeddingi olmayan ürünleri bul
        if find_no_visuals:
            no_visual_products = base_query.filter(Q(visual_embedding__isnull=True))
            self.stdout.write(self.style.WARNING(f"\n{no_visual_products.count()} ürünün görsel embeddingi yok:"))
            
            for product in no_visual_products:
                self.stdout.write(f"ID: {product.id}, Ad: {product.name}, Marka: {product.brand}")
                
                if do_delete and not list_only:
                    product.delete()
                    self.stdout.write(self.style.SUCCESS(f"  -> Silindi"))
        
        # 3. Metin embeddingi olmayan ürünleri bul
        if find_no_text:
            no_text_products = base_query.filter(Q(text_embedding__isnull=True))
            self.stdout.write(self.style.WARNING(f"\n{no_text_products.count()} ürünün metin embeddingi yok:"))
            
            for product in no_text_products:
                self.stdout.write(f"ID: {product.id}, Ad: {product.name}, Marka: {product.brand}")
                
                if do_delete and not list_only:
                    product.delete()
                    self.stdout.write(self.style.SUCCESS(f"  -> Silindi"))
        
        # 4. Eksik bilgileri olan ürünleri bul
        if find_incomplete:
            incomplete_products = base_query.filter(
                Q(name='') | Q(name__isnull=True) |
                Q(image_url='') | Q(image_url__isnull=True)
            )
            self.stdout.write(self.style.WARNING(f"\n{incomplete_products.count()} ürünün eksik bilgileri var:"))
            
            for product in incomplete_products:
                self.stdout.write(f"ID: {product.id}, Ad: {product.name}, URL: {product.image_url}")
                
                if do_delete and not list_only:
                    product.delete()
                    self.stdout.write(self.style.SUCCESS(f"  -> Silindi"))
        
        # 5. Aynı isimli veya benzer ürünleri bul
        if find_duplicates:
            # 5.1 Aynı barkodlu ürünleri bul
            duplicate_barcodes = base_query.exclude(barcode__isnull=True).exclude(barcode='').values('barcode').annotate(
                count=Count('barcode')).filter(count__gt=1).values_list('barcode', flat=True)
            
            if duplicate_barcodes:
                self.stdout.write(self.style.WARNING(f"\n{len(duplicate_barcodes)} adet tekrarlanan barkod bulundu:"))
                
                for barcode in duplicate_barcodes:
                    dupes = base_query.filter(barcode=barcode).order_by('-id')
                    self.stdout.write(f"Barkod: {barcode}, {dupes.count()} ürün:")
                    
                    # Her duplikat ürünü listele
                    for idx, product in enumerate(dupes):
                        self.stdout.write(f"  {idx+1}. ID: {product.id}, Ad: {product.name}, Marka: {product.brand}")
                    
                    # Birleştirme veya silme
                    if do_merge and not list_only and dupes.count() > 1:
                        self._merge_products(dupes)
            
            # 5.2 Benzer isimli ürünleri bul (bu işlem biraz zaman alabilir)
            self.stdout.write("\nBenzer isimli ürünler aranıyor...")
            
            # Pandas DataFrame'e dönüştür (daha hızlı işlem için)
            products_df = pd.DataFrame(list(base_query.values('id', 'name', 'brand', 'barcode')))
            similar_groups = []
            
            # Her ürün adını diğerleriyle karşılaştır
            for i, row in products_df.iterrows():
                if i % 50 == 0:
                    self.stdout.write(f"  İlerleme: {i}/{len(products_df)}")
                
                current_name = row['name'].lower() if pd.notna(row['name']) else ""
                if not current_name:
                    continue
                
                # Bu ürünle benzer olanları bul
                similar_products = []
                
                for j, other_row in products_df.iterrows():
                    if i == j:
                        continue
                    
                    other_name = other_row['name'].lower() if pd.notna(other_row['name']) else ""
                    if not other_name:
                        continue
                    
                    # İsim benzerliğini hesapla
                    similarity = fuzz.token_sort_ratio(current_name, other_name)
                    
                    if similarity >= similarity_threshold:
                        similar_products.append({
                            'id': other_row['id'],
                            'name': other_row['name'],
                            'brand': other_row['brand'],
                            'similarity': similarity
                        })
                
                if similar_products:
                    similar_groups.append({
                        'id': row['id'],
                        'name': row['name'],
                        'brand': row['brand'],
                        'similar': similar_products
                    })
            
            # Benzer ürün gruplarını göster
            if similar_groups:
                self.stdout.write(self.style.WARNING(f"\n{len(similar_groups)} grup benzer isimli ürün bulundu:"))
                
                for idx, group in enumerate(similar_groups):
                    self.stdout.write(f"\nGrup {idx+1}: {group['name']} (ID: {group['id']})")
                    
                    for similar in group['similar']:
                        self.stdout.write(f"  Benzer: {similar['name']} (ID: {similar['id']}, Benzerlik: {similar['similarity']}%)")
                    
                    # Birleştirme
                    if do_merge and not list_only:
                        product_ids = [group['id']] + [s['id'] for s in group['similar']]
                        products_to_merge = base_query.filter(id__in=product_ids)
                        if products_to_merge.count() > 1:
                            self._merge_products(products_to_merge)
            else:
                self.stdout.write("\nBenzer isimli ürün bulunamadı.")
                
        # Özet rapor
        self.stdout.write("\n" + "="*50)
        if list_only:
            self.stdout.write(self.style.SUCCESS("Sadece listeleme yapıldı, herhangi bir değişiklik yapılmadı."))
        else:
            self.stdout.write(self.style.SUCCESS("Temizlik işlemi tamamlandı."))
        
        # Güncel durumu göster
        current_total = Product.objects.count()
        current_with_visual = Product.objects.filter(visual_embedding__isnull=False).count()
        current_with_text = Product.objects.filter(text_embedding__isnull=False).count()
        
        self.stdout.write("\nGüncel Veritabanı Durumu:")
        self.stdout.write(f"✓ Toplam ürün: {current_total}")
        self.stdout.write(f"✓ Görsel embeddingi olan: {current_with_visual}")
        self.stdout.write(f"✓ Metin embeddingi olan: {current_with_text}")
    
    def _merge_products(self, products):
        """İki veya daha fazla ürünü birleştir"""
        products = list(products)
        if not products or len(products) < 2:
            return
        
        try:
            with transaction.atomic():
                # En yeni ürünü ana ürün olarak kabul et
                main_product = products[0]
                duplicate_products = products[1:]
                
                self.stdout.write(f"Ürünler birleştiriliyor: Ana ürün = {main_product.name} (ID: {main_product.id})")
                
                # Her duplikat için
                for dup_product in duplicate_products:
                    self.stdout.write(f"  Birleştiriliyor: {dup_product.name} (ID: {dup_product.id})")
                    
                    # Ana üründe eksik bilgileri doldur
                    if not main_product.brand and dup_product.brand:
                        main_product.brand = dup_product.brand
                    
                    if not main_product.image_url and dup_product.image_url:
                        main_product.image_url = dup_product.image_url
                    
                    if not main_product.image_front_url and dup_product.image_front_url:
                        main_product.image_front_url = dup_product.image_front_url
                    
                    if not main_product.barcode and dup_product.barcode:
                        main_product.barcode = dup_product.barcode
                    
                    # Visual embedding birleştirme
                    if not main_product.visual_embedding and dup_product.visual_embedding:
                        main_product.visual_embedding = dup_product.visual_embedding
                    
                    # Text embedding birleştirme
                    if not main_product.text_embedding and dup_product.text_embedding:
                        main_product.text_embedding = dup_product.text_embedding
                    
                    # Duplikat ürünü sil
                    dup_product.delete()
                
                # Ana ürünü kaydet
                main_product.save()
                
                self.stdout.write(self.style.SUCCESS(f"  -> {len(duplicate_products)} ürün başarıyla birleştirildi"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  -> Birleştirme hatası: {str(e)}"))