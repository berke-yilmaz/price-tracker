# Temel kütüphaneler
import os
import io
import re
import numpy as np
import logging
from datetime import datetime

# CUDA ve TensorFlow uyarılarını bastır
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 0: Tüm loglar, 1: INFO hariç, 2: WARNING hariç, 3: Tüm loglar hariç
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["XLA_PYTHON_CLIENT_ALLOCATOR"] = "platform"

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("product_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# PyTorch
import torch
import torchvision.models as models
import torchvision.transforms as transforms

# FAISS
import faiss

# Görüntü işleme
import cv2
from PIL import Image
from rembg import remove

# NLP ve OCR
from sentence_transformers import SentenceTransformer
import easyocr
import pytesseract
from pyzbar.pyzbar import decode as decode_barcodes
# Model önbelleği
_model_cache = None

def extract_visual_features(image, remove_bg=True, use_gpu=True):
    """
    Görüntüden özellik vektörlerini çıkarır (PyTorch kullanarak)
    
    Args:
        image: PIL.Image, numpy array, BytesIO veya bytes nesnesi olabilir
        remove_bg: Arka planı kaldırma işlemi yapılsın mı?
        use_gpu: GPU kullanılsın mı?
        
    Returns:
        numpy.ndarray: 1280 boyutlu özellik vektörü
    """
    global _model_cache
    
    # GPU kullanılabilirse etkinleştir
    device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")
    
    try:
        # Arka planı kaldır (isteğe bağlı)
        if remove_bg:
            try:
                image_no_bg = remove_background(image)
                image = Image.open(image_no_bg).convert('RGB')
            except Exception as e:
                logger.warning(f"Arka plan kaldırma işleminde hata, orijinal görsel kullanılıyor: {str(e)}")
        
        # Görüntüyü uygun formata dönüştür
        if isinstance(image, (bytes, io.BytesIO)):
            # Eğer image bir BytesIO nesnesi ise
            if isinstance(image, io.BytesIO):
                image_bytes = image.getvalue()
            else:
                image_bytes = image
                
            # Bytes'ı PIL Image'e dönüştür
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        elif isinstance(image, np.ndarray):
            # NumPy array'i PIL Image'e dönüştür
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # Dönüşüm tanımla
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                std=[0.229, 0.224, 0.225]),
        ])
        
        # Görüntüyü işle
        img_tensor = preprocess(image)
        img_tensor = img_tensor.unsqueeze(0).to(device)  # Batch boyutu ekle ve GPU'ya taşı
        
        # Model yükle (statik olarak saklayarak yeniden yüklemeyi önle)
        if _model_cache is None:
            logger.info(f"Use pytorch device_name: {device}")
            _model_cache = models.mobilenet_v2(weights='DEFAULT').to(device)
            # Son sınıflandırma katmanını kaldır
            _model_cache = torch.nn.Sequential(*list(_model_cache.children())[:-1])
            _model_cache.eval()
        
        # Özellik vektörlerini çıkar
        with torch.no_grad():
            try:
                features = _model_cache(img_tensor)
            except RuntimeError as e:
                if "CUDA out of memory" in str(e):
                    logger.warning("CUDA bellek yetersiz, CPU'ya düşülüyor")
                    # GPU belleğini temizle
                    if device.type == 'cuda':
                        torch.cuda.empty_cache()
                    # CPU'da dene
                    return extract_visual_features(image, remove_bg=False, use_gpu=False)
                else:
                    raise
        
        # Tensor'ı numpy array'e dönüştür ve şeklini ayarla
        features = features.cpu().numpy().reshape(-1)
        
        # Bellek temizliği
        del img_tensor
        
        return features
    except Exception as e:
        logger.error(f"Özellik çıkarma hatası: {str(e)}")
        # Hata durumunda CPU'ya düş
        if device.type == 'cuda':
            logger.info("GPU hatası nedeniyle CPU kullanılacak")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return extract_visual_features(image, remove_bg=False, use_gpu=False)
        else:
            # CPU'da da hata varsa yeniden yükselt
            raise

# remove_background fonksiyonunu da güncelliyoruz

def remove_background(image):
    """
    Görsel arka planını kaldır ve işlenmiş görseli döndür.
    """
    try:
        # Önceki CUDA işlemlerinden kalan belleği temizle
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        # Görüntüyü uygun formata dönüştür
        if isinstance(image, Image.Image):
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_data = img_byte_arr.getvalue()
        elif isinstance(image, np.ndarray):
            is_success, buffer = cv2.imencode(".png", image)
            if not is_success:
                raise ValueError("NumPy array'i PNG'ye dönüştürme hatası")
            img_data = buffer.tobytes()
        elif isinstance(image, io.BytesIO):
            img_data = image.getvalue()
        else:
            img_data = image  # bytes türünde olduğunu varsay

        # Sessizce rembg'yi çalıştır
        import sys
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        
        try:
            # Rembg ile arka planı kaldır
            output = remove(img_data)
        finally:
            # stdout/stderr geri yükle
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        # BytesIO nesnesine dönüştür
        result = io.BytesIO(output)
        result.seek(0)
        
        return result
    except Exception as e:
        logger.error(f"Arka plan kaldırma hatası: {str(e)}")
        # Hata durumunda orijinal görseli döndür
        if isinstance(image, io.BytesIO):
            image.seek(0)
            return image
        elif isinstance(image, bytes):
            return io.BytesIO(image)
        elif isinstance(image, Image.Image):
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr
        else:
            # Desteklenmeyen format
            logger.warning("Desteklenmeyen görüntü formatı, boş BytesIO dönüyor")
            return io.BytesIO()

# ProductVectorIndex sınıfı
class ProductVectorIndex:
    def __init__(self):
        self.dimension = 1280  # MobileNetV2 özellik vektörü boyutu 
        self.index = faiss.IndexFlatL2(self.dimension)
        self.product_ids = []
    
    def add_product(self, product_id, feature_vector):
        # Vektör boyutunu kontrol et
        if len(feature_vector) != self.dimension:
            # Boyut uyuşmuyorsa, vektörü yeniden boyutlandır veya hata ver
            # Burada yeniden boyutlandırma tercih edildi
            resized_vector = np.resize(feature_vector, (self.dimension,))
            feature_vector = resized_vector
            
        self.index.add(np.array([feature_vector], dtype=np.float32))
        self.product_ids.append(product_id)
    
    def search(self, feature_vector, k=5):
        # Vektör boyutunu kontrol et
        if len(feature_vector) != self.dimension:
            # Boyut uyuşmuyorsa, vektörü yeniden boyutlandır
            resized_vector = np.resize(feature_vector, (self.dimension,))
            feature_vector = resized_vector
            
        distances, indices = self.index.search(
            np.array([feature_vector], dtype=np.float32), k
        )
        results = [
            {'product_id': self.product_ids[idx], 'distance': float(dist)}
            for idx, dist in zip(indices[0], distances[0])
            if idx != -1 and idx < len(self.product_ids)
        ]
        return results

# Singleton indeks nesnesi
_vector_index = None

def get_vector_index():
    """
    FAISS indeksini döndür veya yoksa oluştur ve doldur
    """
    global _vector_index
    
    if _vector_index is None:
        from .models import Product
        
        _vector_index = ProductVectorIndex()
        
        # Tüm ürünlerin görsel özelliklerini indekse ekle
        products = Product.objects.filter(visual_embedding__isnull=False)
        for product in products:
            _vector_index.add_product(
                product.id, 
                np.array(product.visual_embedding, dtype=np.float32)
            )
    
    return _vector_index

def build_vector_index():
    """
    FAISS indeksini yeniden oluştur (ürün eklendiğinde veya güncellendiğinde)
    """
    global _vector_index
    _vector_index = None
    return get_vector_index()



def scan_barcode(image):
    """
    Görüntüden barkod okuma
    """
    # CV2 formatına dönüştür
    if isinstance(image, (bytes, io.BytesIO)):
        # Eğer image bir BytesIO nesnesi ise
        if isinstance(image, io.BytesIO):
            image = image.getvalue()
        # Bytes'ı numpy array'e dönüştür
        nparr = np.frombuffer(image, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        # Diğer formatlarda (örn. PIL Image, numpy array)
        img = np.array(image)
    
    # Barkodları çözümle
    barcodes = decode_barcodes(img)
    
    # İlk barkodu döndür (varsa)
    if barcodes:
        return barcodes[0].data.decode('utf-8')
    
    return None

def extract_text_from_image(image):
    """
    Görüntüden metin çıkar
    """
    # EasyOCR ile metin çıkarma
    reader = easyocr.Reader(['tr', 'en'])
    results = reader.readtext(image)
    
    # Metinleri birleştir
    texts = [text for _, text, conf in results if conf > 0.5]
    full_text = ' '.join(texts)
    
    return preprocess_text(full_text)

def preprocess_text(text):
    """
    Metni ön işlemden geçirir
    """
    # Küçük harfe dönüştür
    text = text.lower()
    
    # Noktalama işaretlerini kaldır
    text = re.sub(r'[^\w\s]', '', text)
    
    # Stopwords'leri kaldır
    stop_words = set(['ve', 'veya', 'ile', 'için', 'bir', 'bu', 'de', 'da', 'mi', 'ne', 'kim'])
    tokens = text.split()
    tokens = [token for token in tokens if token not in stop_words]
    
    return ' '.join(tokens)

def get_text_embedding(text):
    """
    Metinden vektör oluştur
    """
    model = SentenceTransformer('distiluse-base-multilingual-cased-v1')
    embedding = model.encode(text)
    return embedding

def calculate_text_similarity(embedding1, embedding2):
    """
    İki metin vektörü arasındaki benzerliği hesaplar
    """
    return np.dot(embedding1, embedding2) / (
        np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
    )

def preprocess_image(image, target_size=(224, 224)):
    """
    Görüntüyü işler ve boyutlandırır
    """
    # Görüntüyü uygun formata dönüştür
    if isinstance(image, (bytes, io.BytesIO)):
        # Eğer image bir BytesIO nesnesi ise
        if isinstance(image, io.BytesIO):
            image_bytes = image.getvalue()
        else:
            image_bytes = image
            
        # Bytes'ı numpy array'e dönüştür
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(image, Image.Image):
        # PIL Image'i numpy array'e dönüştür
        img = np.array(image)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        # Diğer formatlarda (örn. numpy array)
        img = image
    
    # Görüntüyü yeniden boyutlandır
    img = cv2.resize(img, target_size)
    
    # Görüntüyü normalize et
    img = img.astype(np.float32) / 255.0
    
    return img

def enhance_for_ocr(image):
    """
    OCR için görüntü kalitesini artır
    """
    # Gri tonlamaya dönüştür
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Gürültü azaltma
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Kontrast artırma
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Eşikleme
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary

def save_processed_image(image, product_id, output_dir="processed_images"):
    """
    İşlenmiş görseli diske kaydet
    
    Args:
        image: İşlenmiş görsel (PIL.Image, BytesIO, bytes veya numpy array)
        product_id: Ürün ID'si
        output_dir: Çıktı dizini
        
    Returns:
        str: Kaydedilen dosyanın yolu
    """
    # Çıktı dizinini oluştur
    os.makedirs(output_dir, exist_ok=True)
    
    # Dosya adını oluştur
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{product_id}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    
    # Görseli dosyaya kaydet
    if isinstance(image, Image.Image):
        image.save(filepath, format='PNG')
    elif isinstance(image, (bytes, io.BytesIO)):
        if isinstance(image, io.BytesIO):
            image_bytes = image.getvalue()
        else:
            image_bytes = image
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
    elif isinstance(image, np.ndarray):
        cv2.imwrite(filepath, image)
    
    return filepath

def identify_product(image, similarity_threshold=0.75):
    """
    Görüntüden ürünü tanımlar.
    Geliştirilmiş sürüm: Arka plan kaldırma işlemi yapılır ve benzerlik eşiği ayarlanabilir.
    
    Args:
        image: Ürün görseli
        similarity_threshold: Benzerlik eşiği (0-1 arası)
        
    Returns:
        Product: Tanımlanan ürün veya None
    """
    # Vector index'i al
    vector_index = get_vector_index()
    
    # Arka planı kaldır
    try:
        image_no_bg = remove_background(image)
        # 1. Görsel işleme - arka planı kaldırılmış görsel üzerinden
        visual_features = extract_visual_features(image_no_bg, remove_bg=False)  # zaten bg kaldırıldı
    except Exception as e:
        logger.warning(f"Arka plan kaldırma hatası, orijinal görsel kullanılıyor: {str(e)}")
        # Arka plan kaldırma başarısız olursa orijinal görseli kullan
        visual_features = extract_visual_features(image, remove_bg=False)
    
    # Aday ürünleri ara
    visual_candidates = vector_index.search(visual_features, k=10)
    
    # Aday ürün yoksa barkod dene
    if not visual_candidates:
        barcode = scan_barcode(image)
        if barcode:
            try:
                from .models import Product
                return Product.objects.get(barcode=barcode)
            except Product.DoesNotExist:
                pass
        return None
    
    # 2. OCR ile metin çıkarma
    extracted_text = extract_text_from_image(image)
    text_embedding = get_text_embedding(extracted_text)
    
    # 3. Aday ürünlerin metin benzerliklerini hesapla
    candidates_with_similarity = []
    from .models import Product
    
    for candidate in visual_candidates:
        try:
            product_id = candidate['product_id']
            product = Product.objects.get(id=product_id)
            
            # Ürün adı ve OCR metni arasındaki benzerlik
            product_text_embedding = get_text_embedding(product.name)
            text_similarity = calculate_text_similarity(text_embedding, product_text_embedding)
            
            # Görsel ve metin benzerliklerini birleştir (ağırlıkları ayarlandı)
            combined_score = 0.7 * (1 - candidate['distance'] / 100) + 0.3 * text_similarity
            
            candidates_with_similarity.append({
                'product': product,
                'visual_score': 1 - candidate['distance'] / 100,
                'text_score': text_similarity,
                'combined_score': combined_score
            })
        except Product.DoesNotExist:
            # Ürün silinmiş olabilir, geç
            continue
    
    # Aday ürün bulunamadıysa barkod dene
    if not candidates_with_similarity:
        barcode = scan_barcode(image)
        if barcode:
            try:
                return Product.objects.get(barcode=barcode)
            except Product.DoesNotExist:
                pass
        return None
    
    # En yüksek benzerlik skoruna sahip ürünü seç
    candidates_with_similarity.sort(key=lambda x: x['combined_score'], reverse=True)
    best_match = candidates_with_similarity[0]
    
    # Eşik değerini kontrol et
    if best_match['combined_score'] > similarity_threshold:
        return best_match['product']
    
    # 4. Barkod okuma (son çare)
    barcode = scan_barcode(image)
    if barcode:
        try:
            return Product.objects.get(barcode=barcode)
        except Product.DoesNotExist:
            pass
    
    # Ürün bulunamadı, yeni eklenmeli
    return None