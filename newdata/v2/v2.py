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
        self.turkish_retail_chains = [
            'migros', 'bim', 'a101', 'şok', 'carrefoursa', 'onur market',
            'hakmar', 'file market', 'tarım kredi', 'kiler market', 'seç market',
            'macro center', 'ekomini', 'bizim toptan', 'metro turkey', 'tespo',
            'tesco kipa', 'real turkey'
        ]
        self.column_order = [
            'barcode', 'name', 'brand', 'category', 'total_images', 
            'retail_type', 'is_private_label', 'country', 'stores',
            'image_url', 'image_front_url', 'image_ingredients_url', 
            'image_nutrition_url', 'image_packaging_url', 'additional_images',
            'weight', 'ingredients', 'id'
        ]
    
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
    
    def has_valid_image_url(self, url):
        """Resim URL'sinin geçerli olduğunu kontrol et"""
        if not url:
            return False
        try:
            response = self.session.head(url, timeout=5)
            content_type = response.headers.get('content-type', '').lower()
            return any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'webp'])
        except:
            return False
    
    def is_turkish_retail_product(self, product):
        """Türk perakende zincirlerinde satılan ürün tespiti"""
        name = product.get('product_name', '') or product.get('product_name_en', '')
        brand = product.get('brands', '')
        countries = product.get('countries', '').lower()
        stores = product.get('stores', '').lower()
        categories = product.get('categories', '').lower()
        
        text_to_check = f"{name} {brand}".lower()
        
        # Debug için reddedilen ürünleri logla
        if not any(chain in stores for chain in self.turkish_retail_chains) and \
           not ('turkey' in countries or 'türkiye' in countries):
            logger.debug(f"Rejected product: {name} ({brand}) - Stores: {stores}, Countries: {countries}")
        
        # 1. Türkiye ülke kontrolü
        if 'turkey' in countries or 'türkiye' in countries:
            return True, 'turkish_origin'
        
        # 2. Türk market zincirlerinde satış kontrolü
        if any(chain in stores for chain in self.turkish_retail_chains):
            return True, 'sold_in_turkish_retail'
        
        # 3. Türk özel markaları (Private Labels)
        turkish_private_labels = [
            # BİM özel markaları
            'dost', 'dost süt', 'dost yogurt', 'dost ayran', 'dost peynir',
            'premium', 'premium quality', 'bim exclusive', 'everyday',
            'smart', 'quality', 'fresh', 'organic choice', 'family',
            
            # ŞOK özel markaları
            'piyale', 'piyale makarna', 'piyale pirinç', 'piyale bulgur',
            'mis', 'mis süt', 'mis yogurt', 'mis ayran', 'mis peynir',
            'mintax', 'mintax deterjan', 'mintax temizlik',
            'gözde', 'gözde yağ', 'şok özel', 'familya', 'comfort',
            'happy home', 'premium quality', 'nostalji',
            
            # A101 özel markaları
            'vera', 'vera deterjan', 'vera temizlik', 'vera hijyen',
            'birşah', 'birşah süt', 'birşah yogurt', 'birşah ayran',
            'happy', 'happy kids', 'clever', 'smart choice',
            'a101 özel', 'everyday needs', 'quality plus', 'basic',
            
            # Migros özel markaları
            'm-label', 'm-classic', 'm-budget', 'migros selection',
            'migros organic', 'migros bio', 'migros premium',
            'migros ekonomik', 'swiss quality', 'migros exclusive',
            'migros fresh', 'migros natural', 'migros kids',
            
            # CarrefourSA özel markaları
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
            'nestle turkey', 'nestle türkiye', 'maggi turkey', 'nescafe turkey',
            'unilever turkey', 'knorr turkey', 'lipton turkey', 'elidor',
            'prima', 'orkid', 'ariel turkey', 'fairy turkey',
            'coca-cola içecek', 'coca-cola turkey', 'fanta turkey', 'sprite turkey',
            'mondelez turkey', 'oreo turkey', 'barilla turkey', 'henkel turkey'
        ]
        
        if any(brand_variant in text_to_check for brand_variant in international_made_in_turkey):
            return True, 'international_made_in_turkey'
        
        # 5. Türk ana markaları
        major_turkish_brands = [
            'ülker', 'eti', 'pınar', 'sütaş', 'içim', 'torku', 'tat', 'koska',
            'şölen', 'elvan', 'dimes', 'tamek', 'beypazarı', 'çaykur', 'doğuş',
            'yörsan', 'sek', 'arifoğlu', 'kurukahveci mehmet efendi',
            'hazer baba', 'hacı bekir', 'hanımeller', 'tadım'
        ]
        
        if any(brand in text_to_check for brand in major_turkish_brands):
            return True, 'major_turkish_brand'
        
        # 6. Türkiye'de popüler uluslararası markalar
        popular_international_in_turkey = [
            'coca-cola', 'pepsi', 'fanta', 'sprite', 'seven up', '7up',
            'schweppes', 'red bull', 'monster', 'burn', 'powerade',
            'fuze tea', 'nestea', 'lipton ice tea', 'cappy', 'tropicana',
            'nutella', 'kinder', 'ferrero rocher', 'kinder bueno',
            'kinder surprise', 'mars', 'snickers', 'twix', 'bounty',
            'milky way', 'toblerone', 'cadbury', 'oreo', 'belvita',
            'trident', 'mentos', 'tic tac', 'haribo', 'skittles',
            'kit kat', 'smarties', 'after eight', 'lion',
            'pringles', 'lays', 'cheetos', 'doritos', 'ruffles',
            'frito lay', 'tortilla', 'nachos', 'popcorn',
            'kellogg', 'cornflakes', 'special k', 'all bran',
            'coco pops', 'frosties', 'nesquik cereal', 'fitness',
            'cheerios', 'granola', 'muesli',
            'barilla', 'pasta', 'spaghetti', 'penne', 'fusilli',
            'knorr', 'maggi', 'heinz', 'ketchup', 'mayonez',
            'hellmanns', 'calve', 'thomy',
            'danone', 'activia', 'actimel', 'milupa', 'aptamil',
            'nestle milk', 'lactaid', 'philadelphia',
            'ariel', 'tide', 'persil', 'fairy', 'domestos',
            'cif', 'vim', 'johnson', 'head shoulders', 'pantene',
            'herbal essences', 'dove', 'nivea', 'loreal',
            'prima', 'pampers', 'huggies', 'orkid', 'baby turco',
            'molfix', 'sleepy', 'uni baby', 'johnson baby',
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
            'dost', 'premium bim', 'piyale', 'mis', 'mintax', 'gözde',
            'vera', 'birşah', 'happy', 'clever', 'm-label', 'm-classic',
            'm-budget', 'migros selection', 'carrefour', 'eco planet',
            'carrefour bio', 'carrefour discount', 'onur', 'hakmar', 'file'
        ]
        
        return any(indicator in text_to_check for indicator in private_label_indicators)
    
    def extract_all_images(self, product):
        """Tüm resim URL'lerini çıkar ve geçerliliğini kontrol et"""
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
        
        # Clean and validate URLs
        clean_urls = []
        for url in image_urls:
            if url and isinstance(url, str) and url.startswith('http'):
                clean_url = url.split('?')[0]
                if clean_url not in clean_urls and self.has_valid_image_url(clean_url):
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
            
            # Türk perakende kontrolü
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
        """Arama fonksiyonu - Rate limit ve retry mantığı ile"""
        products = []
        page = 1
        retries = 3
        
        while len(products) < max_products:
            for attempt in range(retries):
                try:
                    params = {
                        'page': page,
                        'page_size': 24,
                        'fields': 'id,code,product_name,product_name_en,brands,categories,countries,stores,quantity,ingredients_text,ingredients_text_en,images,selected_images,image_url,image_front_url,image_ingredients_url,image_nutrition_url,image_packaging_url',
                        'json': 1,
                        **search_params
                    }
                    
                    response = self.session.get(f"{self.api_url}/search", params=params, timeout=15)
                    if response.status_code == 429:
                        logger.warning(f"Rate limit exceeded, waiting 60 seconds (attempt {attempt+1}/{retries})")
                        time.sleep(60)
                        continue
                    response.raise_for_status()
                    
                    data = response.json()
                    page_products = data.get('products', [])
                    
                    if not page_products:
                        break
                    
                    for product in page_products:
                        product_data = self.extract_product_data(product)
                        if product_data:
                            products.append(product_data)
                            
                            flag = "🏪" if product_data['retail_type'] == 'turkish_private_label' else \
                                   "🇹🇷" if product_data['retail_type'] in ['turkish_origin', 'major_turkish_brand'] else \
                                   "🌍" if product_data['retail_type'] in ['popular_international', 'international_made_in_turkey'] else "🛒"
                            logger.info(f"✓ {flag} {product_data['name']} ({product_data['brand']}) - {product_data['total_images']} images - {product_data['retail_type']}")
                            
                            if len(products) >= max_products:
                                break
                    
                    page += 1
                    time.sleep(0.8)
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    logger.error(f"Search error (attempt {attempt+1}/{retries}): {e}")
                    if attempt + 1 == retries:
                        logger.error(f"Strategy failed after {retries} attempts")
                        return products
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            if not page_products:
                break
        
        return products
    
    def build_search_strategies(self):
        """Türk perakendesine odaklanmış ve önceliklendirilmiş arama stratejileri"""
        strategies = []
        
        # 1. Türk market zincirleri (öncelikli)
        turkish_stores = [
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
            {'stores': 'migros', 'countries': 'turkey'},
            {'stores': 'bim', 'countries': 'turkey'},
            {'stores': 'a101', 'countries': 'turkey'},
            {'stores': 'şok', 'countries': 'turkey'},
            {'stores': 'carrefoursa', 'countries': 'turkey'},
        ]
        strategies.extend(turkish_stores)
        
        # 2. Türk özel markaları (öncelikli)
        private_labels = [
            {'brands': 'dost,dost süt,dost yogurt,premium'},
            {'brands': 'piyale,mis,mintax,gözde,familya,nostalji'},
            {'brands': 'vera,birşah,happy,clever,smart choice'},
            {'brands': 'm-label,m-classic,m-budget,migros selection,migros organic,swiss quality'},
            {'brands': 'carrefour,carrefour bio,eco planet,carrefour selection,carrefour kids'},
            {'brands': 'onur,hakmar,file,kiler exclusive,macro selection,bizim özel,seç özel'},
        ]
        strategies.extend(private_labels)
        
        # 3. Türk ana markaları (öncelikli)
        turkish_brands = [
            {'brands': 'ülker,biskrem,halley,negro,hobby,albeni'},
            {'brands': 'eti,crax,cin,burçak,popkek,browni,tutku,benimo'},
            {'brands': 'pınar,sütaş,içim,yörsan,sek,ariste,banvit'},
            {'brands': 'torku,tat,koska,şölen,elvan'},
            {'brands': 'dimes,tamek,beypazarı,uludağ'},
            {'brands': 'çaykur,doğuş,arifoğlu,tadım'},
            {'brands': 'hacı bekir,hafız mustafa,hanımeller,hazer baba'},
            {'brands': 'kurukahveci mehmet efendi,kahve dünyası,selamlique'},
            {'brands': 'bağdat baharat,dardanel,öncü gıda,naspa,aytac gıda'},
            {'brands': 'bengü gıda,penguen gıda,kent,bolci'},
            {'brands': 'niğde gazozu,sarıyer,kızılay,erikli,hayat su,damla su'},
            {'brands': 'beta tea,ahmad tea turkey,twining turkey'},
        ]
        strategies.extend(turkish_brands)
        
        # 4. Türkiye ülke bazlı
        country_strategies = [
            {'countries': 'turkey'},
            {'countries': 'türkiye'},
        ]
        strategies.extend(country_strategies)
        
        # 5. Türk kategorileri
        turkish_categories = [
            {'categories': 'turkish-products,turkish-sweets,turkish-dairy'},
            {'categories': 'turkish-delight,turkish-coffee,turkish-tea'},
            {'categories': 'turkish-baklava,turkish-ayran,turkish-lokum'},
            {'categories': 'halal-products,made-in-turkey,türkiye-malı'},
            {'categories': 'dairy-products,ayran,yogurt,cheese', 'countries': 'turkey'},
            {'categories': 'beverages,tea,coffee', 'countries': 'turkey'},
        ]
        strategies.extend(turkish_categories)
        
        # 6. Türkiye'de üretilen uluslararası markalar
        international_made_in_turkey = [
            {'brands': 'coca-cola türkiye,fanta turkey,sprite turkey'},
            {'brands': 'nestle türkiye,maggi turkey,nescafe turkey'},
            {'brands': 'unilever turkey,knorr turkey,lipton turkey,elidor'},
            {'brands': 'prima,orkid,ariel turkey,fairy turkey'},
            {'brands': 'mondelez türkiye,oreo turkey,barilla turkey,henkel turkey'},
            {'brands': 'danone türkiye,ferrero türkiye,falım'},
        ]
        strategies.extend(international_made_in_turkey)
        
        # 7. Türkiye'de popüler uluslararası markalar
        international_brands = [
            {'brands': 'coca-cola,pepsi,fanta,sprite,seven up,red bull,monster'},
            {'brands': 'fuze tea,nestea,lipton,cappy,tropicana'},
            {'brands': 'nutella,kinder,ferrero rocher,mars,snickers,twix,bounty'},
            {'brands': 'oreo,toblerone,haribo,mentos,tic tac'},
            {'brands': 'pringles,lays,doritos,cheetos'},
            {'brands': 'kellogg,cornflakes,nesquik'},
            {'brands': 'barilla,knorr,maggi,heinz,hellmanns'},
            {'brands': 'danone,activia,actimel,milupa,aptamil'},
            {'brands': 'pampers,huggies,baby turco,molfix,sleepy,uni baby'},
            {'brands': 'magnum,cornetto,algida,carte dor'},
            {'brands': 'persil,domestos,cif,vim,dove,nivea,loreal'},
            {'brands': 'nestle,unilever,coca-cola,danone,ferrero,mondelez', 'countries': 'turkey'},
        ]
        strategies.extend(international_brands)
        
        # 8. Özel arama terimleri
        search_terms = [
            {'search_terms': 'made in turkey,türkiye malı,turkish brand'},
            {'search_terms': 'migros exclusive,bim private,a101 brand,şok market'},
            {'search_terms': 'private label turkey,özel marka,market markası'},
            {'search_terms': 'halal certified,organik türkiye,doğal ürün'},
            {'search_terms': 'geleneksel türk,artisanal turkey,premium turkey,gourmet turkey'},
        ]
        strategies.extend(search_terms)
        
        return strategies
    
    def collect_turkish_retail_products(self, target=1500):
        """Türk perakende zincirlerinde satılan ürünleri topla"""
        strategies = self.build_search_strategies()
        all_products = []
        products_per_strategy = max(50, target // len(strategies))  # Artırılmış limit
        
        logger.info(f"🇹🇷 TÜRK PERAKENDESİNE ODAKLI ÜRÜN TOPLAMA")
        logger.info(f"🎯 Hedef: {target} Türkiye'de satılan ürün")
        logger.info(f"🏪 Odak: Türk market zincirleri, özel markalar, yerel ürünler")
        logger.info(f"🔍 {len(strategies)} arama stratejisi kullanılacak")
        
        for i, strategy in enumerate(strategies, 1):
            if len(all_products) >= target:
                logger.info(f"🎯 Hedef {target} ürüne ulaşıldı, scraping durduruluyor")
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
                
                # Her 100 üründe ara kaydetme
                if len(all_products) % 100 == 0:
                    self.save_to_csv(all_products, f"intermediate_turkish_retail_products_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
                    logger.info(f"📥 Ara kaydetme: {len(all_products)} ürün")
                
            except Exception as e:
                logger.error(f"Strateji başarısız: {e}")
                continue
        
        return all_products[:target]
    
    def save_to_csv(self, products, filename):
        """CSV olarak kaydet - Mağaza dağılımı ile"""
        if not products:
            logger.warning("Kaydedilecek ürün yok")
            return
        
        df = pd.DataFrame(products)
        available_columns = [col for col in self.column_order if col in df.columns]
        df = df[available_columns]
        
        df.to_csv(filename, index=False, encoding='utf-8')
        
        # İstatistikler
        total = len(products)
        avg_images = sum(p['total_images'] for p in products) / total
        retail_distribution = df['retail_type'].value_counts()
        private_label_count = sum(1 for p in products if p.get('is_private_label', False))
        
        # Mağaza dağılımı
        store_counts = df['stores'].str.lower().str.split(',').explode().str.strip().value_counts()
        turkish_stores = [store for store in store_counts.index if any(chain in store for chain in self.turkish_retail_chains)]
        
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
        
        logger.info(f"   🏪 En popüler market zincirleri:")
        for store in turkish_stores[:5]:
            count = store_counts.get(store, 0)
            logger.info(f"      {store}: {count} ürün")
        
        top_brands = df['brand'].value_counts().head(5)
        logger.info(f"   🏆 En popüler markalar: {', '.join(top_brands.index.tolist())}")

def main():
    scraper = TurkishRetailFocusedScraper()
    
    TARGET = 1500
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
        scraper.save_to_csv(products, f"interrupted_{OUTPUT_FILE}")
        logger.info(f"💾 Kesilen veri {len(products)} ürün ile kaydedildi")
    except Exception as e:
        logger.error(f"❌ Hata: {e}")
        scraper.save_to_csv(products, f"error_{OUTPUT_FILE}")
        logger.info(f"💾 Hata sonrası veri {len(products)} ürün ile kaydedildi")

if __name__ == "__main__":
    main()