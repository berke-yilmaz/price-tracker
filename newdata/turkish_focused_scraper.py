# turkish_retail_focused_scraper.py - Türkiye'de satılan ürünlere odaklanan scraper
import requests
import pandas as pd
import time
import json
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TurkishRetailFocusedScraper:
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org"
        self.api_url = f"{self.base_url}/api/v2"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TurkishRetailScraper/1.0 (Educational Purpose)',
            'Accept': 'application/json'
        })
        
        self.collected_barcodes = set()
        self.total_collected = 0
        self.turkish_retail_products = 0
        self.international_in_turkey = 0
        self.private_label_products = 0
        
    def is_latin_alphabet_only(self, text):
        """Latin alfabe kontrolü - Türkçe karakterler dahil"""
        if not text:
            return False
        
        text = str(text).strip()
        if len(text) < 2:
            return False
        
        clean_text = re.sub(r'[0-9\s\-\.\,\(\)\[\]\&\%\+\*\/\'\"\:\;\!\?\=]', '', text)
        
        if len(clean_text) == 0:
            return True
        
        for char in clean_text:
            if not (
                ('A' <= char <= 'Z') or ('a' <= char <= 'z') or
                char in 'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿčšž' or
                char in 'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸČŠŽ' or
                char in 'çğıöşüÇĞİÖŞÜ'
            ):
                return False
        
        return True
    
    def is_turkish_retail_product(self, product):
        """Türk perakende zincirlerinde satılan ürün tespiti"""
        name = product.get('product_name', '') or product.get('product_name_en', '')
        brand = product.get('brands', '')
        countries = product.get('countries', '').lower()
        stores = product.get('stores', '').lower()
        categories = product.get('categories', '').lower()
        
        text_to_check = f"{name} {brand}".lower()
        
        # 1. Türkiye ülke kontrolü
        if 'turkey' in countries or 'türkiye' in countries:
            return True, 'turkish_origin'
        
        # 2. Türk market zincirlerinde satış kontrolü
        turkish_retail_chains = [
            'migros', 'bim', 'a101', 'şok', 'carrefoursa', 'onur market',
            'hakmar', 'file market', 'tarım kredi', 'kiler market', 'seç market',
            'macro center', 'ekomini', 'bizim toptan', 'metro turkey'
        ]
        
        if any(chain in stores for chain in turkish_retail_chains):
            return True, 'sold_in_turkish_retail'
        
        # 3. Türk özel markaları (Private Labels)
        # KAPSAMLI TÜRK ÖZEL MARKA LİSTESİ
        turkish_private_labels = [
            # BİM özel markaları (detaylı)
            'dost', 'dost süt', 'dost yogurt', 'dost ayran', 'dost peynir',
            'premium', 'premium quality', 'bim exclusive', 'everyday',
            'smart', 'quality', 'fresh', 'organic choice', 'family',
            
            # ŞOK özel markaları (detaylı)
            'piyale', 'piyale makarna', 'piyale pirinç', 'piyale bulgur',
            'mis', 'mis süt', 'mis yogurt', 'mis ayran', 'mis peynir',
            'mintax', 'mintax deterjan', 'mintax temizlik',
            'gözde', 'gözde yağ', 'şok özel', 'familya', 'comfort',
            'happy home', 'premium quality', 'nostalji',
            
            # A101 özel markaları (detaylı)
            'vera', 'vera deterjan', 'vera temizlik', 'vera hijyen',
            'birşah', 'birşah süt', 'birşah yogurt', 'birşah ayran',
            'happy', 'happy kids', 'clever', 'smart choice',
            'a101 özel', 'everyday needs', 'quality plus', 'basic',
            
            # Migros özel markaları (detaylı)
            'm-label', 'm-classic', 'm-budget', 'migros selection',
            'migros organic', 'migros bio', 'migros premium',
            'migros ekonomik', 'swiss quality', 'migros exclusive',
            'migros fresh', 'migros natural', 'migros kids',
            
            # CarrefourSA özel markaları (detaylı)
            'carrefour', 'carrefour bio', 'carrefour discount',
            'carrefour selection', 'carrefour kids', 'carrefour organic',
            'carrefour premium', 'eco planet', 'carrefour classic',
            'carrefour home', 'carrefour fresh', 'carrefour gourmet',
            
            # Diğer zincir özel markaları
            'onur', 'onur selection', 'hakmar', 'hakmar özel',
            'file', 'file quality', 'kiler exclusive', 'kiler özel',
            'macro selection', 'bizim özel', 'bizim quality',
            'seç market', 'seç özel'
        ]
        
        if any(label in text_to_check for label in turkish_private_labels):
            return True, 'turkish_private_label'
        
        # 4. Türkiye'de üretilen uluslararası markalar
        international_made_in_turkey = [
            # Türkiye'de üretilen Nestlé ürünleri
            'nestle turkey', 'nestle türkiye', 'maggi turkey', 'nescafe turkey',
            
            # Türkiye'de üretilen Unilever ürünleri
            'unilever turkey', 'knorr turkey', 'lipton turkey', 'elidor',
            
            # Türkiye'de üretilen P&G ürünleri
            'prima', 'orkid', 'ariel turkey', 'fairy turkey',
            
            # Türkiye'de üretilen Coca-Cola ürünleri
            'coca-cola içecek', 'coca-cola turkey', 'fanta turkey', 'sprite turkey',
            
            # Türkiye'de üretilen diğer markalar
            'mondelez turkey', 'oreo turkey', 'barilla turkey', 'henkel turkey'
        ]
        
        if any(brand_variant in text_to_check for brand_variant in international_made_in_turkey):
            return True, 'international_made_in_turkey'
        
        # 5. Türk ana markaları
        major_turkish_brands = [
            # Gıda markaları
            'ülker', 'eti', 'pınar', 'sütaş', 'içim', 'torku', 'tat', 'koska',
            'şölen', 'elvan', 'dimes', 'tamek', 'beypazarı', 'çaykur', 'doğuş',
            
            # Yerel/bölgesel markalar
            'yörsan', 'sek', 'arifoğlu', 'kurukahveci mehmet efendi',
            'hazer baba', 'hacı bekir', 'hanımeller', 'tadım'
        ]
        
        if any(brand in text_to_check for brand in major_turkish_brands):
            return True, 'major_turkish_brand'
        
        # 6. Türkiye'de popüler uluslararası markalar (adapte edilmiş)
        # KAPSAMLI ULUSLARARASI MARKA LİSTESİ (TÜRKİYE'DE POPÜLER)
        popular_international_in_turkey = [
            # İçecek markaları
            'coca-cola', 'pepsi', 'fanta', 'sprite', 'seven up', '7up',
            'schweppes', 'red bull', 'monster', 'burn', 'powerade',
            'fuze tea', 'nestea', 'lipton ice tea', 'cappy', 'tropicana',
            
            # Şekerleme ve çikolata
            'nutella', 'kinder', 'ferrero rocher', 'kinder bueno',
            'kinder surprise', 'mars', 'snickers', 'twix', 'bounty',
            'milky way', 'toblerone', 'cadbury', 'oreo', 'belvita',
            'trident', 'mentos', 'tic tac', 'haribo', 'skittles',
            'kit kat', 'smarties', 'after eight', 'lion',
            
            # Atıştırmalık ve cips
            'pringles', 'lays', 'cheetos', 'doritos', 'ruffles',
            'frito lay', 'tortilla', 'nachos', 'popcorn',
            
            # Kahvaltı ve tahıl
            'kellogg', 'cornflakes', 'special k', 'all bran',
            'coco pops', 'frosties', 'nesquik cereal', 'fitness',
            'cheerios', 'granola', 'muesli',
            
            # Makarna ve hazır yemek
            'barilla', 'pasta', 'spaghetti', 'penne', 'fusilli',
            'knorr', 'maggi', 'heinz', 'ketchup', 'mayonez',
            'hellmanns', 'calve', 'thomy',
            
            # Süt ürünleri (uluslararası)
            'danone', 'activia', 'actimel', 'milupa', 'aptamil',
            'nestle milk', 'lactaid', 'philadelphia',
            
            # Temizlik ve kişisel bakım
            'ariel', 'tide', 'persil', 'fairy', 'domestos',
            'cif', 'vim', 'johnson', 'head shoulders', 'pantene',
            'herbal essences', 'dove', 'nivea', 'loreal',
            
            # Bebek ürünleri
            'prima', 'pampers', 'huggies', 'orkid', 'baby turco',
            'molfix', 'sleepy', 'uni baby', 'johnson baby',
            
            # Dondurma
            'magnum', 'cornetto', 'algida', 'carte dor',
            'ben jerry', 'haagen dazs', 'twister', 'calippo'
        ]
        
        if any(intl_brand in text_to_check for intl_brand in popular_international_in_turkey):
            return True, 'popular_international'
        
        return False, 'not_in_turkish_retail'
    
    def is_private_label_product(self, product):
        """Özel marka ürün kontrolü"""
        name = product.get('product_name', '') or product.get('product_name_en', '')
        brand = product.get('brands', '')
        
        text_to_check = f"{name} {brand}".lower()
        
        private_label_indicators = [
            # BİM
            'dost', 'premium bim',
            # ŞOK
            'piyale', 'mis', 'mintax', 'gözde',
            # A101
            'vera', 'birşah', 'happy', 'clever',
            # Migros
            'm-label', 'm-classic', 'm-budget', 'migros selection',
            # CarrefourSA
            'carrefour', 'eco planet', 'carrefour bio', 'carrefour discount',
            # Diğer zincirler
            'onur', 'hakmar', 'file'
        ]
        
        return any(indicator in text_to_check for indicator in private_label_indicators)
    
    def extract_all_images(self, product):
        """Tüm resim URL'lerini çıkar"""
        image_urls = []
        
        # Method 1: selected_images
        selected_images = product.get('selected_images', {})
        for img_type in ['front', 'ingredients', 'nutrition', 'packaging']:
            if img_type in selected_images:
                display_imgs = selected_images[img_type].get('display', {})
                for lang, url in display_imgs.items():
                    if url and url not in image_urls:
                        image_urls.append(url)
        
        # Method 2: images object
        images = product.get('images', {})
        for img_id, img_data in images.items():
            if isinstance(img_data, dict):
                for size in ['full', 'display', 'small', 'thumb']:
                    if size in img_data and img_data[size]:
                        url = img_data[size]
                        if url not in image_urls:
                            image_urls.append(url)
        
        # Method 3: Direct fields
        direct_fields = [
            'image_url', 'image_front_url', 'image_ingredients_url',
            'image_nutrition_url', 'image_packaging_url'
        ]
        for field in direct_fields:
            if field in product and product[field]:
                url = product[field]
                if url not in image_urls:
                    image_urls.append(url)
        
        # Clean URLs
        clean_urls = []
        for url in image_urls:
            if url and isinstance(url, str) and url.startswith('http'):
                clean_url = url.split('?')[0]
                if clean_url not in clean_urls:
                    clean_urls.append(clean_url)
        
        return clean_urls
    
    def extract_product_data(self, product):
        """Ürün verisi çıkarma - Türk perakende odaklı"""
        try:
            name = product.get('product_name', '') or product.get('product_name_en', '')
            brand = product.get('brands', '').split(',')[0].strip() if product.get('brands') else ''
            barcode = product.get('code', '')
            
            # Latin alfabe kontrolü
            if not name or not self.is_latin_alphabet_only(name):
                return None
            
            if brand and not self.is_latin_alphabet_only(brand):
                return None
            
            # Duplicate kontrolü
            if barcode in self.collected_barcodes:
                return None
            
            # Türk perakende kontrolü - ANA FİLTRE
            is_in_turkish_retail, retail_type = self.is_turkish_retail_product(product)
            if not is_in_turkish_retail:
                return None
            
            # Resim kontrolü
            all_image_urls = self.extract_all_images(product)
            if len(all_image_urls) < 1:
                return None
            
            # İstatistik güncelleme
            if retail_type == 'turkish_origin' or retail_type == 'major_turkish_brand':
                self.turkish_retail_products += 1
            elif retail_type == 'popular_international' or retail_type == 'international_made_in_turkey':
                self.international_in_turkey += 1
            elif retail_type == 'turkish_private_label':
                self.private_label_products += 1
            
            # Özel marka kontrolü
            is_private_label = self.is_private_label_product(product)
            
            # Resim verisi hazırla
            image_data = {
                'image_url': all_image_urls[0] if all_image_urls else '',
                'image_front_url': '',
                'image_ingredients_url': '',
                'image_nutrition_url': '',
                'image_packaging_url': '',
                'additional_images': json.dumps(all_image_urls[1:] if len(all_image_urls) > 1 else [])
            }
            
            # Selected images'den özel resimler
            selected_images = product.get('selected_images', {})
            
            if 'front' in selected_images:
                front_display = selected_images['front'].get('display', {})
                if front_display:
                    image_data['image_front_url'] = list(front_display.values())[0]
                    
            if 'ingredients' in selected_images:
                ing_display = selected_images['ingredients'].get('display', {})
                if ing_display:
                    image_data['image_ingredients_url'] = list(ing_display.values())[0]
                    
            if 'nutrition' in selected_images:
                nut_display = selected_images['nutrition'].get('display', {})
                if nut_display:
                    image_data['image_nutrition_url'] = list(nut_display.values())[0]
                    
            if 'packaging' in selected_images:
                pack_display = selected_images['packaging'].get('display', {})
                if pack_display:
                    image_data['image_packaging_url'] = list(pack_display.values())[0]
            
            # Kategori
            categories = product.get('categories', '')
            main_category = ''
            if categories:
                cat_list = [c.strip() for c in categories.split(',')]
                for cat in cat_list:
                    if len(cat) > 3 and not any(x in cat.lower() for x in ['en:', 'fr:', 'food', 'foods']):
                        main_category = cat
                        break
                main_category = main_category or (cat_list[0] if cat_list else '')
            
            # Final product data
            product_data = {
                'id': product.get('id', ''),
                'barcode': barcode,
                'name': name.strip(),
                'brand': brand.strip() if brand else 'Unknown',
                'category': main_category,
                'weight': product.get('quantity', ''),
                'ingredients': (product.get('ingredients_text_en', '') or 
                              product.get('ingredients_text', ''))[:500],
                'total_images': len(all_image_urls),
                'retail_type': retail_type,
                'is_private_label': is_private_label,
                'country': product.get('countries', ''),
                'stores': product.get('stores', ''),
                **image_data
            }
            
            self.collected_barcodes.add(barcode)
            self.total_collected += 1
            
            return product_data
            
        except Exception as e:
            logger.error(f"Error extracting product: {e}")
            return None
    
    def search_products(self, search_params, max_products=100):
        """Arama fonksiyonu"""
        products = []
        page = 1
        
        while len(products) < max_products:
            try:
                params = {
                    'page': page,
                    'page_size': 24,
                    'fields': 'id,code,product_name,product_name_en,brands,categories,countries,stores,quantity,ingredients_text,ingredients_text_en,images,selected_images,image_url,image_front_url,image_ingredients_url,image_nutrition_url,image_packaging_url',
                    'json': 1,
                    **search_params
                }
                
                response = self.session.get(f"{self.api_url}/search", params=params, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                page_products = data.get('products', [])
                
                if not page_products:
                    break
                
                for product in page_products:
                    product_data = self.extract_product_data(product)
                    if product_data:
                        products.append(product_data)
                        
                        # Ürün tipi göstergesi
                        if product_data['retail_type'] == 'turkish_private_label':
                            flag = "🏪"
                        elif product_data['retail_type'] in ['turkish_origin', 'major_turkish_brand']:
                            flag = "🇹🇷"
                        elif product_data['retail_type'] in ['popular_international', 'international_made_in_turkey']:
                            flag = "🌍"
                        else:
                            flag = "🛒"
                        
                        logger.info(f"✓ {flag} {product_data['name']} ({product_data['brand']}) - {product_data['total_images']} images - {product_data['retail_type']}")
                        
                        if len(products) >= max_products:
                            break
                
                page += 1
                time.sleep(0.8)
                
            except Exception as e:
                logger.error(f"Search error: {e}")
                time.sleep(2)
                break
        
        return products
    
    def collect_turkish_retail_products(self, target=1200):
        """Türk perakende zincirlerinde satılan ürünleri topla"""
                    
        # TÜRK PERAKENDESİNE ODAKLI ARAMA STRATEJİLERİ (MASİF GENIŞLETME)
        strategies = [
            # 1. TÜRK MARKET ZİNCİRLERİ (Genişletilmiş)
            {'stores': 'migros'},
            {'stores': 'bim'},
            {'stores': 'a101'},
            {'stores': 'şok'},
            {'stores': 'carrefoursa'},
            {'stores': 'onur market'},
            {'stores': 'hakmar'},
            {'stores': 'file market'},
            {'stores': 'tarım kredi'},
            {'stores': 'kiler market'},
            {'stores': 'macro center'},
            {'stores': 'seç market'},
            {'stores': 'ekomini'},
            {'stores': 'bizim toptan'},
            {'stores': 'metro turkey'},
            {'stores': 'tespo'},
            {'stores': 'tesco kipa'},
            {'stores': 'real turkey'},
            
            # 2. TÜRK ÖZEL MARKALARI (Masif Genişletme)
            # BİM özel markaları
            {'brands': 'dost'},
            {'brands': 'dost süt'},
            {'brands': 'dost yogurt'},
            {'brands': 'premium'},
            {'brands': 'everyday'},
            {'brands': 'smart'},
            
            # ŞOK özel markaları
            {'brands': 'piyale'},
            {'brands': 'mis'},
            {'brands': 'mintax'},
            {'brands': 'gözde'},
            {'brands': 'familya'},
            {'brands': 'nostalji'},
            
            # A101 özel markaları
            {'brands': 'vera'},
            {'brands': 'birşah'},
            {'brands': 'happy'},
            {'brands': 'clever'},
            {'brands': 'smart choice'},
            
            # Migros özel markaları
            {'brands': 'm-label'},
            {'brands': 'm-classic'},
            {'brands': 'm-budget'},
            {'brands': 'migros selection'},
            {'brands': 'migros organic'},
            {'brands': 'swiss quality'},
            
            # CarrefourSA özel markaları
            {'brands': 'carrefour'},
            {'brands': 'carrefour bio'},
            {'brands': 'eco planet'},
            {'brands': 'carrefour selection'},
            {'brands': 'carrefour kids'},
            
            # 3. TÜRK ANA MARKALARI (Büyük Genişletme)
            # Yıldız Holding markaları
            {'brands': 'ülker'},
            {'brands': 'biskrem'},
            {'brands': 'halley'},
            {'brands': 'negro'},
            {'brands': 'hobby'},
            {'brands': 'albeni'},
            {'brands': 'mcvities turkey'},
            {'brands': 'godiva turkey'},
            
            # Eti Gıda markaları
            {'brands': 'eti'},
            {'brands': 'crax'},
            {'brands': 'cin'},
            {'brands': 'burçak'},
            {'brands': 'popkek'},
            {'brands': 'browni'},
            {'brands': 'tutku'},
            {'brands': 'benimo'},
            
            # Süt ürünleri markaları
            {'brands': 'pınar'},
            {'brands': 'sütaş'},
            {'brands': 'içim'},
            {'brands': 'yörsan'},
            {'brands': 'sek'},
            {'brands': 'ariste'},
            {'brands': 'banvit'},
            
            # Diğer Türk markaları
            {'brands': 'torku'},
            {'brands': 'tat'},
            {'brands': 'koska'},
            {'brands': 'şölen'},
            {'brands': 'elvan'},
            {'brands': 'dimes'},
            {'brands': 'tamek'},
            {'brands': 'beypazarı'},
            {'brands': 'uludağ'},
            {'brands': 'çaykur'},
            {'brands': 'doğuş'},
            {'brands': 'arifoğlu'},
            {'brands': 'tadım'},
            
            # 4. TÜRKİYE'DE ÜRETİLEN ULUSLARARASI MARKALAR
            {'brands': 'coca-cola türkiye'},
            {'brands': 'nestle türkiye'},
            {'brands': 'unilever türkiye'},
            {'brands': 'mondelez türkiye'},
            {'brands': 'danone türkiye'},
            {'brands': 'ferrero türkiye'},
            {'brands': 'elidor'},
            {'brands': 'prima'},
            {'brands': 'orkid'},
            {'brands': 'falım'},
            
            # 5. POPÜLER ULUSLARARASI MARKALAR (Masif Genişletme)
            # İçecekler
            {'brands': 'coca-cola'},
            {'brands': 'pepsi'},
            {'brands': 'fanta'},
            {'brands': 'sprite'},
            {'brands': 'seven up'},
            {'brands': 'red bull'},
            {'brands': 'monster'},
            {'brands': 'burn'},
            {'brands': 'fuze tea'},
            {'brands': 'nestea'},
            {'brands': 'lipton'},
            {'brands': 'cappy'},
            
            # Şekerleme
            {'brands': 'nutella'},
            {'brands': 'kinder'},
            {'brands': 'ferrero rocher'},
            {'brands': 'mars'},
            {'brands': 'snickers'},
            {'brands': 'twix'},
            {'brands': 'bounty'},
            {'brands': 'oreo'},
            {'brands': 'toblerone'},
            {'brands': 'haribo'},
            {'brands': 'mentos'},
            {'brands': 'tic tac'},
            
            # Atıştırmalık
            {'brands': 'pringles'},
            {'brands': 'lays'},
            {'brands': 'doritos'},
            {'brands': 'cheetos'},
            
            # Kahvaltı
            {'brands': 'kellogg'},
            {'brands': 'cornflakes'},
            {'brands': 'nesquik'},
            
            # Makarna ve soslar
            {'brands': 'barilla'},
            {'brands': 'knorr'},
            {'brands': 'maggi'},
            {'brands': 'heinz'},
            {'brands': 'hellmanns'},
            
            # 6. TÜRK KATEGORİLERİ (Genişletilmiş)
            {'categories': 'turkish-products'},
            {'categories': 'turkish-sweets'},
            {'categories': 'turkish-dairy'},
            {'categories': 'turkish-delight'},
            {'categories': 'turkish-coffee'},
            {'categories': 'turkish-tea'},
            {'categories': 'turkish-baklava'},
            {'categories': 'turkish-ayran'},
            {'categories': 'turkish-lokum'},
            {'categories': 'halal-products'},
            {'categories': 'made-in-turkey'},
            {'categories': 'türkiye-malı'},
            
            # 7. TÜRKİYE ÜLKESİ
            {'countries': 'turkey'},
            {'countries': 'türkiye'},
            
            # 8. GENEL KATEGORİLER (Türk pazarında popüler)
            {'categories': 'dairy-products'},
            {'categories': 'yogurt'},
            {'categories': 'milk'},
            {'categories': 'cheese'},
            {'categories': 'ayran'},
            {'categories': 'beverages'},
            {'categories': 'soft-drinks'},
            {'categories': 'fruit-juices'},
            {'categories': 'water'},
            {'categories': 'snacks'},
            {'categories': 'chips'},
            {'categories': 'crackers'},
            {'categories': 'nuts'},
            {'categories': 'chocolates'},
            {'categories': 'candies'},
            {'categories': 'biscuits'},
            {'categories': 'cookies'},
            {'categories': 'breakfast-cereals'},
            {'categories': 'tea'},
            {'categories': 'coffee'},
            {'categories': 'pasta'},
            {'categories': 'sauces'},
            {'categories': 'condiments'},
            {'categories': 'preserves'},
            {'categories': 'honey'},
            {'categories': 'olive-oil'},
            {'categories': 'sunflower-oil'},
            {'categories': 'ice-cream'},
            {'categories': 'frozen-foods'},
            
            # 9. ÖZEL ARAMA TERİMLERİ (Genişletilmiş)
            {'search_terms': 'made in turkey'},
            {'search_terms': 'türkiye malı'},
            {'search_terms': 'turkish brand'},
            {'search_terms': 'migros exclusive'},
            {'search_terms': 'bim private'},
            {'search_terms': 'a101 brand'},
            {'search_terms': 'şok market'},
            {'search_terms': 'carrefour turkey'},
            {'search_terms': 'private label turkey'},
            {'search_terms': 'özel marka'},
            {'search_terms': 'market markası'},
            {'search_terms': 'discount brand'},
            {'search_terms': 'ekonomik marka'},
            {'search_terms': 'halal certified'},
            {'search_terms': 'organik türkiye'},
            {'search_terms': 'doğal ürün'},
            {'search_terms': 'geleneksel türk'},
            {'search_terms': 'artisanal turkey'},
            {'search_terms': 'premium turkey'},
            {'search_terms': 'gourmet turkey'},
            
            # 10. MAĞAZA KOMBINASYONLARI
            {'stores': 'migros', 'countries': 'turkey'},
            {'stores': 'bim', 'countries': 'turkey'},
            {'stores': 'a101', 'countries': 'turkey'},
            {'stores': 'şok', 'countries': 'turkey'},
            {'stores': 'carrefoursa', 'countries': 'turkey'},
            
            # 11. MARKA + ÜLKE KOMBINASYONLARI
            {'brands': 'nestle', 'countries': 'turkey'},
            {'brands': 'unilever', 'countries': 'turkey'},
            {'brands': 'coca-cola', 'countries': 'turkey'},
            {'brands': 'danone', 'countries': 'turkey'},
            {'brands': 'ferrero', 'countries': 'turkey'},
            {'brands': 'mondelez', 'countries': 'turkey'},
            
            # 12. KATEGORİ + ÜLKE KOMBINASYONLARI
            {'categories': 'dairy-products', 'countries': 'turkey'},
            {'categories': 'beverages', 'countries': 'turkey'},
            {'categories': 'snacks', 'countries': 'turkey'},
            {'categories': 'chocolates', 'countries': 'turkey'},
            {'categories': 'biscuits', 'countries': 'turkey'},
            
            # 13. EK TÜRK BÖLGESEL/YEREL MARKALAR
            {'brands': 'hacı bekir'},
            {'brands': 'hafız mustafa'},
            {'brands': 'hanımeller'},
            {'brands': 'hazer baba'},
            {'brands': 'kurukahveci mehmet efendi'},
            {'brands': 'kahve dünyası'},
            {'brands': 'selamlique'},
            {'brands': 'bağdat baharat'},
            {'brands': 'dardanel'},
            {'brands': 'öncü gıda'},
            {'brands': 'naspa'},
            {'brands': 'aytac gıda'},
            {'brands': 'bengü gıda'},
            {'brands': 'penguen gıda'},
            {'brands': 'kent'},
            {'brands': 'bolci'},
            
            # 14. EK İÇECEK MARKALARI
            {'brands': 'niğde gazozu'},
            {'brands': 'sarıyer'},
            {'brands': 'kızılay'},
            {'brands': 'erikli'},
            {'brands': 'hayat su'},
            {'brands': 'damla su'},
            {'brands': 'beta tea'},
            {'brands': 'ahmad tea turkey'},
            {'brands': 'twining turkey'},
            
            # 15. EK ULUSLARARASI MARKALAR
            {'brands': 'philadelphia'},
            {'brands': 'activia'},
            {'brands': 'actimel'},
            {'brands': 'milupa'},
            {'brands': 'aptamil'},
            {'brands': 'pampers'},
            {'brands': 'huggies'},
            {'brands': 'baby turco'},
            {'brands': 'molfix'},
            {'brands': 'sleepy'},
            {'brands': 'uni baby'},
            {'brands': 'johnson baby'},
            {'brands': 'magnum'},
            {'brands': 'cornetto'},
            {'brands': 'algida'},
            {'brands': 'carte dor'},
            {'brands': 'calippo'},
            {'brands': 'twister'},
            {'brands': 'persil'},
            {'brands': 'domestos'},
            {'brands': 'cif'},
            {'brands': 'vim'},
            {'brands': 'dove'},
            {'brands': 'nivea'},
            {'brands': 'loreal'},
            {'brands': 'herbal essences'}
        
        ]
        
        all_products = []
        products_per_strategy = max(30, target // len(strategies))
        
        logger.info(f"🇹🇷 TÜRK PERAKENDESİNE ODAKLI ÜRÜN TOPLAMA")
        logger.info(f"🎯 Hedef: {target} Türkiye'de satılan ürün")
        logger.info(f"🏪 Odak: Türk market zincirleri, özel markalar, yerel ürünler")
        logger.info(f"🔍 {len(strategies)} arama stratejisi kullanılacak")
        
        for i, strategy in enumerate(strategies, 1):
            if len(all_products) >= target:
                break
            
            logger.info(f"\n📋 Strateji {i}/{len(strategies)}: {strategy}")
            
            try:
                new_products = self.search_products(strategy, products_per_strategy)
                
                # Duplicate kontrolü
                unique_products = []
                existing_barcodes = {p['barcode'] for p in all_products}
                
                for product in new_products:
                    if product['barcode'] not in existing_barcodes:
                        unique_products.append(product)
                        existing_barcodes.add(product['barcode'])
                
                all_products.extend(unique_products)
                
                logger.info(f"✅ {len(unique_products)} yeni ürün eklendi")
                logger.info(f"📊 Toplam: {len(all_products)}/{target}")
                
                # İstatistikler
                if len(all_products) > 0:
                    avg_images = sum(p['total_images'] for p in all_products) / len(all_products)
                    logger.info(f"🖼️  Ortalama resim sayısı: {avg_images:.1f}")
                    logger.info(f"🇹🇷 Türk ürünleri: {self.turkish_retail_products}")
                    logger.info(f"🌍 Uluslararası (TR'de): {self.international_in_turkey}")
                    logger.info(f"🏪 Özel markalar: {self.private_label_products}")
                
            except Exception as e:
                logger.error(f"Strateji başarısız: {e}")
                continue
        
        return all_products
    
    def save_to_csv(self, products, filename):
        """CSV olarak kaydet"""
        if not products:
            logger.warning("Kaydedilecek ürün yok")
            return
        
        df = pd.DataFrame(products)
        
        # Kolon sırası
        column_order = [
            'barcode', 'name', 'brand', 'category', 'total_images', 
            'retail_type', 'is_private_label', 'country', 'stores',
            'image_url', 'image_front_url', 'image_ingredients_url', 
            'image_nutrition_url', 'image_packaging_url', 'additional_images',
            'weight', 'ingredients', 'id'
        ]
        
        available_columns = [col for col in column_order if col in df.columns]
        df = df[available_columns]
        
        df.to_csv(filename, index=False, encoding='utf-8')
        
        # İstatistikler
        total = len(products)
        avg_images = sum(p['total_images'] for p in products) / total
        
        # Retail type dağılımı
        retail_distribution = df['retail_type'].value_counts()
        private_label_count = sum(1 for p in products if p.get('is_private_label', False))
        
        logger.info(f"\n💾 {total} ürün {filename} dosyasına kaydedildi")
        logger.info(f"📊 SON İSTATİSTİKLER:")
        logger.info(f"   🖼️  Ortalama resim sayısı: {avg_images:.2f}")
        logger.info(f"   🏪 Özel marka ürünleri: {private_label_count} ({private_label_count/total*100:.1f}%)")
        logger.info(f"   🏷️  Benzersiz marka sayısı: {df['brand'].nunique()}")
        logger.info(f"   📂 En popüler kategoriler: {', '.join(df['category'].value_counts().head(3).index.tolist())}")
        
        logger.info(f"   📈 Perakende tipi dağılımı:")
        for retail_type, count in retail_distribution.items():
            percentage = (count / total) * 100
            logger.info(f"      {retail_type}: {count} ({percentage:.1f}%)")
        
        # En popüler markalar
        top_brands = df['brand'].value_counts().head(5)
        logger.info(f"   🏆 En popüler markalar: {', '.join(top_brands.index.tolist())}")

def main():
    scraper = TurkishRetailFocusedScraper()
    
    TARGET = 1500  # Türk perakendesi için hedef
    OUTPUT_FILE = f"turkish_retail_products_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    logger.info("🇹🇷 TÜRK PERAKENDESİNE ODAKLI ÜRÜN SCRAPER'I")
    logger.info(f"🎯 Hedef: {TARGET} Türkiye'de satılan ürün")
    logger.info(f"🏪 Odak: BİM, Migros, A101, ŞOK, CarrefourSA ve diğer Türk zincirleri")
    logger.info(f"🏷️  Özel markalar, Türk markaları ve Türkiye'de popüler uluslararası markalar")
    logger.info(f"📝 Latin alfabe + Türkçe karakterler")
    
    try:
        start_time = time.time()
        
        products = scraper.collect_turkish_retail_products(TARGET)
        
        if products:
            scraper.save_to_csv(products, OUTPUT_FILE)
            
            elapsed = time.time() - start_time
            logger.info(f"\n🎉 BAŞARILI! {elapsed/60:.1f} dakikada tamamlandı")
            logger.info(f"✅ {len(products)} Türk perakende ürünü toplandı")
            logger.info(f"💾 Dosya: {OUTPUT_FILE}")
            
            print(f"\n📋 SONRAKİ ADIMLAR:")
            print(f"1. Django'ya aktar:")
            print(f"   python manage.py import_products {OUTPUT_FILE} \\")
            print(f"      --process-images --skip-existing --limit 0")
            print(f"")
            print(f"2. Mevcut verilerle birleştir:")
            print(f"   cat latin_products_20250614_2050.csv {OUTPUT_FILE} > combined_turkish_retail.csv")
            print(f"")
            print(f"3. İstatistikleri kontrol et:")
            print(f"   python manage.py shell")
            print(f"   >>> from api.models import Product")
            print(f"   >>> Product.objects.count()")
            
        else:
            logger.error("❌ Hiç ürün toplanamadı!")
            
    except KeyboardInterrupt:
        logger.info("⏹️ Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()