#!/usr/bin/env python3
# api/management/commands/delete_products.py
from django.core.management.base import BaseCommand
from api.models import Product
from django.db import transaction
import logging

class Command(BaseCommand):
    help = 'Veritabanındaki ürünleri temizle/sil'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Tüm ürünleri sil')
        parser.add_argument('--category', type=str, help='Belirli bir kategorideki ürünleri sil')
        parser.add_argument('--confirm', action='store_true', help='Silme işlemini onayla')
        parser.add_argument('--brand', type=str, help='Belirli bir markadaki ürünleri sil')
        parser.add_argument('--id-range', type=str, help='ID aralığındaki ürünleri sil (örn: 50-100)')

    def handle(self, *args, **options):
        delete_all = options['all']
        category = options['category']
        confirm = options['confirm']
        brand = options['brand']
        id_range = options['id_range']
        
        # Sorguyu oluştur
        query = Product.objects.all()
        
        # Filtreleme
        if category:
            query = query.filter(category=category)
            filter_msg = f"kategori='{category}'"
        elif brand:
            query = query.filter(brand=brand)
            filter_msg = f"marka='{brand}'"
        elif id_range:
            try:
                start_id, end_id = map(int, id_range.split('-'))
                query = query.filter(id__gte=start_id, id__lte=end_id)
                filter_msg = f"ID aralığı={id_range}"
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Geçersiz ID aralığı: {id_range}. Örnek format: 50-100"))
                return
        elif delete_all:
            filter_msg = "TÜM ÜRÜNLER"
        else:
            self.stdout.write(self.style.ERROR("Silme işlemi için bir kriter belirtmelisiniz (--all, --category, --brand veya --id-range)"))
            return
        
        # Silinecek ürün sayısı
        total_to_delete = query.count()
        
        if total_to_delete == 0:
            self.stdout.write(self.style.WARNING(f"Silinecek ürün bulunamadı: {filter_msg}"))
            return
        
        # Onay iste
        if not confirm:
            self.stdout.write(self.style.WARNING(f"⚠️ DİKKAT! {total_to_delete} ürün silinecek ({filter_msg})."))
            self.stdout.write(self.style.WARNING("Bu işlem geri alınamaz. Onaylamak için --confirm parametresini ekleyin."))
            self.stdout.write(self.style.WARNING("Örnek: python manage.py delete_products --all --confirm"))
            return
        
        # Silme işlemi
        try:
            with transaction.atomic():
                deleted_count = query.delete()[0]
                self.stdout.write(self.style.SUCCESS(f"Başarıyla {deleted_count} ürün silindi!"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Silme işlemi sırasında hata: {str(e)}"))
        
        # Güncel durumu göster
        remaining = Product.objects.count()
        self.stdout.write(f"\nVeri tabanında kalan ürün sayısı: {remaining}")