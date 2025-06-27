# api/util.py - REWIRED TO USE THE FIXED PREPROCESSOR
import os
import io
import re
import numpy as np
import logging
from typing import List, Dict, Optional, Union
from functools import lru_cache
import cv2

# --- Core Library Imports ---
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from torchvision.models import ResNet50_Weights
import faiss
from PIL import Image
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
import colorsys
from google.cloud import vision

# --- Local Imports ---
from .models import Product
from django.conf import settings
# <<< FIX: Import the single, corrected preprocessor >>>
from .enhanced_preprocessor import EnhancedProductPreprocessor

# --- Setup ---
logger = logging.getLogger(__name__)

if hasattr(Image, 'Resampling'):
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
else:
    RESAMPLING_FILTER = Image.ANTIALIAS

# =============================================================================
# ⭐ PROCESS-SAFE MODEL CACHING ⭐
# =============================================================================
_MODEL_CACHE = {}
def get_process_safe_model(model_key: str, loader_func):
    pid = os.getpid()
    cache_key = f"{model_key}_{pid}"
    if cache_key not in _MODEL_CACHE:
        logger.info(f"Process {pid}: Loading model '{model_key}'...")
        _MODEL_CACHE[cache_key] = loader_func()
        logger.info(f"Process {pid}: Model '{model_key}' loaded and cached.")
    return _MODEL_CACHE[cache_key]

# --- Model Loaders ---
def _load_resnet():
    device = torch.device("cpu")
    model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2).to(device)
    feature_extractor = torch.nn.Sequential(*list(model.children())[:-1])
    feature_extractor.eval()
    return feature_extractor

def _load_sentence_transformer():
    return SentenceTransformer('distiluse-base-multilingual-cased-v1')

# <<< FIX: Loader for the corrected preprocessor >>>
def _load_preprocessor():
    use_gpu = getattr(settings, 'AI_USE_GPU', False)
    return EnhancedProductPreprocessor(target_size=(512, 512), use_gpu=use_gpu)

def get_resnet_model():
    return get_process_safe_model('resnet', _load_resnet)

def get_sentence_transformer_model():
    return get_process_safe_model('sentence_transformer', _load_sentence_transformer)

def get_preprocessor():
    return get_process_safe_model('preprocessor', _load_preprocessor)

# ... (Keep the GOOGLE VISION and FAISS sections exactly as they are) ...
# =============================================================================
# ⭐ GOOGLE VISION CLIENT (NOT CACHED) ⭐
# =============================================================================
def get_google_vision_client() -> Optional[vision.ImageAnnotatorClient]:
    try:
        return vision.ImageAnnotatorClient()
    except Exception as e:
        logger.error(f"Failed to create Google Vision client instance: {e}")
        return None

# =============================================================================
# ⭐ VECTOR INDEX (FAISS) MANAGEMENT (UNCHANGED) ⭐
# =============================================================================
class SimpleVectorIndex:
    def __init__(self, dimension=2048):
        self.dimension = dimension
        self.color_indices = {}
        all_colors = [choice[0] for choice in Product.COLOR_CHOICES]
        for color in all_colors:
            self.color_indices[color] = {'index': faiss.IndexFlatL2(self.dimension), 'product_ids': []}

    def add_product(self, product_id: int, feature_vector: np.ndarray, color_category: str):
        if color_category not in self.color_indices: color_category = 'unknown'
        index_data = self.color_indices[color_category]
        index_data['index'].add(np.array([feature_vector], dtype=np.float32))
        index_data['product_ids'].append(product_id)

    def search(self, feature_vector: np.ndarray, search_categories: List[str], k: int) -> List[Dict]:
        all_results = []
        categories_to_search = set(search_categories)
        if not categories_to_search: categories_to_search.add('unknown')
        for category in categories_to_search:
            if category not in self.color_indices: continue
            index_data = self.color_indices[category]
            if index_data['index'].ntotal == 0: continue
            k_for_category = min(k, index_data['index'].ntotal)
            distances, indices = index_data['index'].search(np.array([feature_vector], dtype=np.float32), k_for_category)
            for i, dist in zip(indices[0], distances[0]):
                if i != -1:
                    all_results.append({'product_id': index_data['product_ids'][i], 'distance': float(dist), 'color_category': category})
        unique_results = {res['product_id']: res for res in sorted(all_results, key=lambda x: x['distance'])}
        return sorted(list(unique_results.values()), key=lambda x: x['distance'])[:k]

def _build_full_vector_index():
    vector_index = SimpleVectorIndex()
    products_with_features = Product.objects.filter(processing_status='completed', visual_embedding__isnull=False).values_list('id', 'visual_embedding', 'color_category')
    for p_id, p_embedding, p_color in products_with_features:
        if p_embedding:
            vector_index.add_product(p_id, np.array(p_embedding, dtype=np.float32), p_color)
    return vector_index

def get_vector_index():
    return get_process_safe_model('vector_index', _build_full_vector_index)

def build_vector_index():
    pid = os.getpid()
    cache_key = f"vector_index_{pid}"
    if cache_key in _MODEL_CACHE: del _MODEL_CACHE[cache_key]
    logger.info(f"Process {pid}: Cleared old vector index. It will be rebuilt on next access.")
    return get_vector_index()

# =============================================================================
# CORE AI & IMAGE PROCESSING FUNCTIONS
# =============================================================================
def _get_bytes_from_input(image_input: Union[Image.Image, bytes, io.BytesIO]) -> bytes:
    if isinstance(image_input, bytes): return image_input
    if isinstance(image_input, io.BytesIO): return image_input.getvalue()
    if isinstance(image_input, Image.Image):
        with io.BytesIO() as output:
            format = 'PNG' if image_input.mode == 'RGBA' else 'JPEG'
            image_input.save(output, format=format)
            return output.getvalue()
    raise TypeError("Unsupported image input type")

# <<< FIX: The @lru_cache was preventing the product_id from being passed. Removing it. >>>
# The preprocessor itself is cached per-process, which is sufficient.
def _preprocess_image(image_bytes: bytes, product_id: Optional[str] = None) -> Image.Image:
    """
    Central preprocessing function now correctly uses the robust preprocessor
    and passes the product_id for debugging.
    """
    preprocessor = get_preprocessor()
    # <<< FIX: Pass the product_id to the process_image method >>>
    results = preprocessor.process_image(image_bytes, return_steps=True, product_id=product_id)
    
    if results['success'] and results['processed_image']:
        return results['processed_image']
    else:
        logger.warning(f"Preprocessor failed for {product_id}: {results.get('error')}. Using basic fallback.")
        return Image.open(io.BytesIO(image_bytes)).convert('RGB').resize((512, 512))

def extract_visual_features_resnet(image_input: Union[Image.Image, bytes, io.BytesIO], product_id: Optional[str] = None, **kwargs) -> np.ndarray:
    try:
        image_bytes = _get_bytes_from_input(image_input)
        # <<< FIX: Pass product_id through >>>
        processed_image = _preprocess_image(image_bytes, product_id=product_id)
        
        # This part remains the same
        preprocess_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        img_tensor = preprocess_transform(processed_image).unsqueeze(0)
        model = get_resnet_model()
        with torch.no_grad():
            features = model(img_tensor)
        return features.cpu().numpy().reshape(-1)
    except Exception as e:
        logger.error(f"Feature extraction failed for {product_id}: {e}", exc_info=True)
        return np.zeros(2048, dtype=np.float32)

def categorize_by_color(image_input: Union[Image.Image, bytes, io.BytesIO], product_id: Optional[str] = None) -> Dict:
    try:
        image_bytes = _get_bytes_from_input(image_input)
        # <<< FIX: Pass product_id through >>>
        processed_image = _preprocess_image(image_bytes, product_id=product_id)
        
        # This part remains the same
        img_for_color = processed_image.resize((150, 150), RESAMPLING_FILTER)
        pixels = np.array(img_for_color).reshape(-1, 3)
        mask = (np.mean(pixels, axis=1) > 15) & (np.mean(pixels, axis=1) < 240)
        filtered_pixels = pixels[mask]
        if len(filtered_pixels) < 10:
            kmeans = KMeans(n_clusters=min(5, len(pixels) if len(pixels)>0 else 1), random_state=42, n_init='auto').fit(pixels if len(pixels)>0 else [[128,128,128]])
        else:
            kmeans = KMeans(n_clusters=min(5, len(filtered_pixels)), random_state=42, n_init='auto').fit(filtered_pixels)
        dominant_colors = kmeans.cluster_centers_.astype(int).tolist()
        color_votes, total_weight = {}, 0
        for i, rgb in enumerate(dominant_colors):
            weight=1.0/(i+1);total_weight+=weight;r,g,b=[x/255.0 for x in rgb];h,s,v=colorsys.rgb_to_hsv(r,g,b);h,s,v=h*360,s*100,v*100
            category='black' if v<15 else 'white' if v>85 and s<15 else 'white' if s<20 and v>60 else 'black' if s<20 else 'brown' if 10<=h<=30 and 30<=s<=100 and 15<=v<=65 else 'red' if h>=345 or h<=15 else 'orange' if 15<h<=45 else 'yellow' if 45<h<=75 else 'green' if 75<h<=150 else 'blue' if 150<h<=250 else 'purple' if 250<h<=300 else 'pink' if 300<h<345 else 'unknown'
            color_votes[category]=color_votes.get(category,0)+weight
        best_category,secondary_category,confidence='unknown',None,0.0
        if color_votes:
            sorted_votes=sorted(color_votes.items(),key=lambda item:item[1],reverse=True)
            if sorted_votes:best_category=sorted_votes[0][0];confidence=sorted_votes[0][1]/total_weight if total_weight>0 else 0.0
            if len(sorted_votes)>1:secondary_category=sorted_votes[1][0]
            if confidence<0.3:best_category='unknown'
        return {'category':best_category,'secondary_category':secondary_category,'confidence':confidence,'colors':dominant_colors}
    except Exception as e:
        logger.error(f"Color analysis FAILED for {product_id}: {e}", exc_info=True)
        return {'category':'unknown','secondary_category':None,'confidence':0.0,'colors':[]}
    
def get_color_aware_text_embedding(text: str, color_category: str) -> np.ndarray:
    model = get_sentence_transformer_model()
    color_map = {choice[0]: choice[1] for choice in Product.COLOR_CHOICES}
    enhanced_text = f"{text} {color_map.get(color_category, '')}".strip()
    return model.encode(enhanced_text)

def extract_text_from_product_image(image_bytes: bytes) -> Dict:
    client = get_google_vision_client()
    if not client: return {'success': False, 'error': 'Google Vision client could not be created', 'text': ''}
    try:
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        if response.error.message: raise Exception(f"Vision API Error: {response.error.message}")
        full_text = response.text_annotations[0].description if response.text_annotations else ""
        return {'success': True, 'text': full_text}
    except Exception as e:
        logger.error(f"OCR with Google Vision failed: {e}"); return {'success': False, 'error': str(e), 'text': ''}

def calculate_cosine_similarity(vec1, vec2) -> float:
    try:
        if vec1 is None or vec2 is None: return 0.0
        vec1 = np.asarray(vec1, dtype=np.float32)
        vec2 = np.asarray(vec2, dtype=np.float32)
        if vec1.shape != vec2.shape: return 0.0
        norm1, norm2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0: return 0.0
        dot_product = np.dot(vec1, vec2)
        similarity = dot_product / (norm1 * norm2)
        return float(np.nan_to_num(similarity))
    except Exception:
        return 0.0

# <<< FIX: RESTORED identify_product FUNCTION >>>
def identify_product(image_input: Union[Image.Image, bytes, io.BytesIO], similarity_threshold: float = 0.7) -> Optional[Product]:
    try:
        image_bytes = _get_bytes_from_input(image_input)
        visual_features = extract_visual_features_resnet(image_bytes)
        vector_index = get_vector_index()
        
        if all(v['index'].ntotal == 0 for v in vector_index.color_indices.values()): 
            logger.warning("Identify Product: Vector index is empty.")
            return None
            
        all_categories = list(vector_index.color_indices.keys())
        candidates = vector_index.search(visual_features, search_categories=all_categories, k=1)
        
        if not candidates: return None
            
        best_candidate = candidates[0]
        similarity = max(0.0, 1.0 - (best_candidate['distance'] / 150.0))
        
        logger.info(f"Identify Product: Best match is product ID {best_candidate['product_id']} with similarity {similarity:.2f}")
        
        if similarity >= similarity_threshold: 
            return Product.objects.get(id=best_candidate['product_id'])
        return None
        
    except Product.DoesNotExist: 
        return None
    except Exception as e: 
        logger.error(f"Product identification failed: {e}", exc_info=True)
        return None

# <<< FIX: RESTORED extract_product_info_from_text FUNCTION >>>
def extract_product_info_from_text(text: str) -> Dict:
    """Extract product information from OCR text"""
    if not text or not isinstance(text, str): 
        return {'name': '', 'brand': '', 'weight': ''}
        
    dairy_brands = ['SÜTAŞ', 'PINAR', 'İÇİM', 'TORKU', 'YÖRSAN', 'KEBİR', 'SEK', 'DANONE', 'ALTINKILIÇ', 'Eker']
    beverage_brands = ['COCA-COLA', 'PEPSI', 'FRUKO', 'YEDİGÜN', 'ULUDAG', 'SİRMA', 'ERİKLİ', 'NESTLE PURE LIFE', 'BEYPAZARI', 'KIZILAY', 'LIPTON', 'DOĞUŞ ÇAY', 'ÇAYKUR']
    snack_brands = ['ÜLKER', 'ETİ', 'ŞÖLEN', 'TADIM', 'KENT', 'LAY\'S', 'RUFFLES', 'DORITOS', 'CHEETOS', 'MİLFÖY']
    pantry_brands = ['FİLİZ', 'NUHUN ANKARA', 'BARİLLA', 'KNORR', 'YUDUM', 'ORKİDE', 'TARİŞ', 'TUKAŞ', 'TAT', 'DARDANEL', 'SUPERFRESH']
    cosmetic_brands = ['ARKO', 'DALAN', 'HACI ŞAKİR', 'DERBY', 'GILLETTE']
    
    known_brands = sorted(dairy_brands + beverage_brands + snack_brands + pantry_brands + cosmetic_brands, key=len, reverse=True)
    weight_regex = re.compile(r"(\d[\d.,]*\s*(?:kg|g|gr|ml|l|lt|litre|cl|cc|adet|x|'li)\b)", re.IGNORECASE)
    
    text = text.replace('|', '\n').replace(' - ', '\n')
    lines = [line.strip() for line in text.split('\n') if line.strip() and len(line) > 1]
    
    found_brand, found_weight, potential_names = '', '', []
    
    for line in lines:
        if not found_brand:
            for brand in known_brands:
                if re.search(r'\b' + re.escape(brand) + r'\b', line, re.IGNORECASE):
                    found_brand = brand.title(); break
        weight_match = weight_regex.search(line)
        if weight_match and not found_weight:
            found_weight = weight_match.group(1).lower()

    for line in lines:
        is_brand_line = found_brand and (found_brand.lower() in line.lower())
        is_weight_line = weight_regex.fullmatch(line)
        is_junk = re.fullmatch(r'[\d\s.,]+', line) or 'içindekiler' in line.lower() or 'ingredients' in line.lower()
        if not is_brand_line and not is_weight_line and not is_junk:
            potential_names.append(line)
            
    product_name = max(potential_names, key=len) if potential_names else max(lines, key=len) if lines else ''
    
    if product_name and found_brand: product_name = re.sub(r'\b' + re.escape(found_brand) + r'\b', '', product_name, flags=re.IGNORECASE).strip()
    if product_name and found_weight: product_name = re.sub(re.escape(found_weight), '', product_name, flags=re.IGNORECASE).strip()
    
    if not found_brand and product_name:
        first_word = product_name.split()[0]
        for brand in known_brands:
            if first_word.upper() == brand:
                found_brand = brand.title(); product_name = ' '.join(product_name.split()[1:]); break
    
    return {'name': product_name.strip(), 'brand': found_brand.strip(), 'weight': found_weight.strip()}