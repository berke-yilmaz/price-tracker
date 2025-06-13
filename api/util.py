# api/util.py - Enhanced Color-Based Categorization with ResNet
import os
import io
import re
import numpy as np
from datetime import datetime
from typing import Tuple, List, Dict, Optional
import colorsys

# CUDA and TensorFlow warnings suppression
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["XLA_PYTHON_CLIENT_ALLOCATOR"] = "platform"

# Add this at the top of api/util_enhanced.py if it's missing

import logging

# Create logger for this module
logger = logging.getLogger(__name__)

# Alternative: If you want to ensure logger exists everywhere
try:
    logger
except NameError:
    logger = logging.getLogger(__name__)

# Or use this safer approach throughout the code:
def get_logger():
    """Get or create logger safely"""
    try:
        return logger
    except NameError:
        return logging.getLogger(__name__)

# Then in your code, replace logger.info() with:
# get_logger().info()

# Or simply add this one-liner at the top after other imports:
logger = logging.getLogger(__name__)

# PyTorch and Computer Vision
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from torchvision.models import ResNet50_Weights

# FAISS for vector search
import faiss

# Image processing
import cv2
from PIL import Image, ImageEnhance
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# NLP and OCR
from sentence_transformers import SentenceTransformer
import easyocr
import pytesseract
from pyzbar.pyzbar import decode as decode_barcodes

# Model cache
_model_cache = {}

# Color categories with improved definitions
COLOR_CATEGORIES = {
    'red': {
        'name': 'Kırmızı',
        'hue_range': [(345, 360), (0, 15)],  # Red spans around 0° in HSV
        'keywords': ['kırmızı', 'red', 'cherry', 'kiraz', 'pomegranate', 'nar']
    },
    'orange': {
        'name': 'Turuncu',
        'hue_range': [(15, 45)],
        'keywords': ['turuncu', 'orange', 'portakal', 'mandarin']
    },
    'yellow': {
        'name': 'Sarı',
        'hue_range': [(45, 75)],
        'keywords': ['sarı', 'yellow', 'lemon', 'limon', 'banana', 'muz']
    },
    'green': {
        'name': 'Yeşil',
        'hue_range': [(75, 150)],
        'keywords': ['yeşil', 'green', 'lime', 'misket', 'spinach', 'ıspanak']
    },
    'blue': {
        'name': 'Mavi',
        'hue_range': [(150, 250)],
        'keywords': ['mavi', 'blue', 'navy', 'lacivert']
    },
    'purple': {
        'name': 'Mor',
        'hue_range': [(250, 300)],
        'keywords': ['mor', 'purple', 'violet', 'menekşe', 'grape', 'üzüm']
    },
    'pink': {
        'name': 'Pembe',
        'hue_range': [(300, 345)],
        'keywords': ['pembe', 'pink', 'rose', 'gül']
    },
    'white': {
        'name': 'Beyaz',
        'lightness_range': (80, 100),
        'keywords': ['beyaz', 'white', 'milk', 'süt', 'cream', 'krema']
    },
    'black': {
        'name': 'Siyah',
        'lightness_range': (0, 20),
        'keywords': ['siyah', 'black', 'dark', 'koyu']
    },
    'brown': {
        'name': 'Kahverengi',
        'hue_range': [(10, 30)],
        'saturation_range': (30, 100),
        'lightness_range': (15, 65),
        'keywords': ['kahverengi', 'brown', 'chocolate', 'çikolata', 'coffee', 'kahve']
    }
}

def extract_dominant_colors(image, n_colors=5):
    """
    Extract dominant colors from image using K-means clustering
    
    Args:
        image: PIL Image or numpy array
        n_colors: Number of dominant colors to extract
        
    Returns:
        List of dominant colors in RGB format
    """
    try:
        # Convert to numpy array if needed
        if isinstance(image, Image.Image):
            img_array = np.array(image)
        else:
            img_array = image
        
        # Reshape image to be a list of pixels
        pixels = img_array.reshape((-1, 3))
        
        # Remove very dark and very light pixels (likely background/noise)
        brightness = np.mean(pixels, axis=1)
        mask = np.logical_and(brightness > 20, brightness < 235)
        filtered_pixels = pixels[mask]
        
        if len(filtered_pixels) < n_colors:
            logger.warning("Not enough valid pixels for color analysis")
            return pixels[:n_colors].tolist()
        
        # Sample pixels if too many (for performance)
        if len(filtered_pixels) > 10000:
            indices = np.random.choice(len(filtered_pixels), 10000, replace=False)
            filtered_pixels = filtered_pixels[indices]
        
        # Apply K-means clustering
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(filtered_pixels)
        
        # Get cluster centers (dominant colors)
        colors = kmeans.cluster_centers_.astype(int)
        
        # Sort colors by cluster size (most dominant first)
        labels = kmeans.labels_
        unique_labels, counts = np.unique(labels, return_counts=True)
        sorted_indices = np.argsort(counts)[::-1]
        
        dominant_colors = [colors[i].tolist() for i in sorted_indices]
        
        logger.debug(f"Extracted {len(dominant_colors)} dominant colors")
        return dominant_colors
        
    except Exception as e:
        logger.error(f"Dominant color extraction error: {str(e)}")
        return []

def rgb_to_hsv(rgb):
    """Convert RGB to HSV"""
    r, g, b = [x/255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return (h*360, s*100, v*100)

def classify_single_color(hue, saturation, value):
    """
    Classify a single HSV color into predefined categories
    Enhanced version with better color detection
    
    Args:
        hue: Hue value (0-360)
        saturation: Saturation value (0-100)  
        value: Value/Lightness (0-100)
        
    Returns:
        str: Color category name
    """
    
    # Handle very dark colors (black/dark)
    if value < 15:
        return 'black'
    
    # Handle very light colors with low saturation (white/light)
    if value > 85 and saturation < 15:
        return 'white'
    
    # Handle low saturation colors (gray, but we'll classify as white for products)
    if saturation < 20:
        if value > 60:
            return 'white'
        else:
            return 'black'
    
    # Handle brown (special case - orange with low lightness)
    if 10 <= hue <= 30 and saturation >= 30 and 15 <= value <= 65:
        return 'brown'
    
    # Standard color wheel classification with broader ranges
    if hue >= 345 or hue <= 15:        # Red
        return 'red'
    elif 15 < hue <= 45:               # Orange  
        return 'orange'
    elif 45 < hue <= 75:               # Yellow
        return 'yellow'
    elif 75 < hue <= 150:              # Green
        return 'green'
    elif 150 < hue <= 250:             # Blue
        return 'blue'
    elif 250 < hue <= 300:             # Purple
        return 'purple'
    elif 300 < hue < 345:              # Pink/Magenta
        return 'pink'
    
    # Fallback
    return 'unknown'

def categorize_by_color(image):
    """
    Categorize product by its dominant color with improved analysis
    
    Args:
        image: PIL Image, numpy array, BytesIO or bytes object
        
    Returns:
        Dict with color category info
    """
    try:
        from PIL import Image as PILImage
        
        # Convert image to PIL if needed
        if isinstance(image, (bytes, io.BytesIO)):
            if isinstance(image, io.BytesIO):
                image_data = image.getvalue()
            else:
                image_data = image
            pil_image = PILImage.open(io.BytesIO(image_data)).convert('RGB')
        elif isinstance(image, np.ndarray):
            pil_image = PILImage.fromarray(image)
        elif hasattr(image, 'convert'):
            pil_image = image.convert('RGB')
        else:
            pil_image = PILImage.open(image).convert('RGB')
        
        # Extract dominant colors using K-means
        dominant_colors = extract_dominant_colors(pil_image, n_colors=5)
        
        if not dominant_colors:
            logger.warning("No dominant colors found")
            return {'category': 'unknown', 'confidence': 0.0, 'colors': []}
        
        # Convert to HSV for better color classification
        hsv_colors = []
        for rgb in dominant_colors:
            try:
                h, s, v = rgb_to_hsv(rgb)
                hsv_colors.append((h, s, v))
            except Exception as e:
                logger.warning(f"HSV conversion error: {e}")
                continue
        
        if not hsv_colors:
            return {'category': 'unknown', 'confidence': 0.0, 'colors': dominant_colors}
        
        # Classify each dominant color and vote
        color_votes = {}
        total_weight = 0
        
        for i, (h, s, v) in enumerate(hsv_colors):
            # Weight by dominance (first color gets more weight)
            weight = 1.0 / (i + 1)
            total_weight += weight
            
            category = classify_single_color(h, s, v)
            
            if category in color_votes:
                color_votes[category] += weight
            else:
                color_votes[category] = weight
            
            logger.debug(f"Color {i}: HSV({h:.1f}, {s:.1f}, {v:.1f}) -> {category} (weight: {weight:.2f})")
        
        # Find the most voted category
        if color_votes:
            best_category = max(color_votes, key=color_votes.get)
            confidence = color_votes[best_category] / total_weight
            
            # Apply confidence threshold
            if confidence < 0.3:
                best_category = 'unknown'
                confidence = 0.0
            
            logger.info(f"Color analysis result: {best_category} (confidence: {confidence:.3f})")
            logger.debug(f"All votes: {color_votes}")
        else:
            best_category = 'unknown'
            confidence = 0.0
        
        return {
            'category': best_category,
            'confidence': confidence,
            'colors': dominant_colors,
            'hsv_colors': hsv_colors,
            'color_votes': color_votes
        }
        
    except Exception as e:
        logger.error(f"Color categorization error: {str(e)}")
        return {'category': 'unknown', 'confidence': 0.0, 'colors': []}


def save_processed_image(image_data, product_identifier, output_dir):
    """
    Save processed image to directory
    
    Args:
        image_data: BytesIO image data
        product_identifier: Product ID or barcode for filename
        output_dir: Directory to save to
        
    Returns:
        str: Path to saved image
    """
    try:
        from PIL import Image as PILImage
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        filename = f"{product_identifier}_processed.png"
        filepath = os.path.join(output_dir, filename)
        
        # Save image
        if hasattr(image_data, 'seek'):
            image_data.seek(0)
            
        image = PILImage.open(image_data)
        image.save(filepath, 'PNG')
        
        return filepath
        
    except Exception as e:
        logger.error(f"Error saving processed image: {str(e)}")
        return None
    
def safe_remove_background(image):
    """
    Safely remove background with fallback to original image
    
    Args:
        image: PIL Image
        
    Returns:
        tuple: (processed_image, success_flag)
    """
    try:
        from rembg import remove
        from PIL import Image as PILImage
        import io
        
        # Convert image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Remove background
        output = remove(img_bytes)
        processed_image = PILImage.open(io.BytesIO(output))
        
        # Check if background removal was safe
        if is_background_removal_safe(image, processed_image):
            return processed_image, True
        else:
            return image, False
            
    except Exception as e:
        logger.warning(f"Background removal error: {e}")
        return image, False

def extract_visual_features_resnet(image, remove_bg=True, use_gpu=True, color_category=None):
    """
    Fixed version of ResNet feature extraction that handles RGBA properly
    
    Args:
        image: PIL.Image, numpy array, BytesIO or bytes object
        remove_bg: Remove background?
        use_gpu: Use GPU if available?
        color_category: Color category for optimized processing
        
    Returns:
        numpy.ndarray: 2048-dimensional feature vector (ResNet50)
    """
    global _model_cache
    
    # GPU setup
    device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")
    
    try:
        # Background removal (optional)
        if remove_bg:
            try:
                image_no_bg, bg_success = safe_remove_background(image)
                if bg_success:
                    image = image_no_bg
                else:
                    logger.warning("Background removal failed, using original image")
            except Exception as e:
                logger.warning(f"Background removal error, using original: {str(e)}")
        
        # Convert image to appropriate format and ensure RGB
        if isinstance(image, (bytes, io.BytesIO)):
            if isinstance(image, io.BytesIO):
                image_bytes = image.getvalue()
            else:
                image_bytes = image
            image = Image.open(io.BytesIO(image_bytes))
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # CRITICAL FIX: Ensure image is RGB (not RGBA)
        if image.mode == 'RGBA':
            # Create a white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Color-aware preprocessing
        if color_category:
            image = enhance_for_color_category(image, color_category)
        
        # ResNet50 preprocessing
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225]),
        ])
        
        # Process image
        img_tensor = preprocess(image)
        img_tensor = img_tensor.unsqueeze(0).to(device)
        
        # Load ResNet50 model (cached)
        model_key = f"resnet50_{device}"
        if model_key not in _model_cache:
            logger.info(f"Loading ResNet50 on device: {device}")
            resnet50 = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2).to(device)
            # Remove the final classification layer to get features
            _model_cache[model_key] = torch.nn.Sequential(*list(resnet50.children())[:-1])
            _model_cache[model_key].eval()
        
        # Extract features
        with torch.no_grad():
            try:
                features = _model_cache[model_key](img_tensor)
            except RuntimeError as e:
                if "CUDA out of memory" in str(e):
                    logger.warning("CUDA memory insufficient, falling back to CPU")
                    if device.type == 'cuda':
                        torch.cuda.empty_cache()
                    return extract_visual_features_resnet_fixed(image, remove_bg=False, use_gpu=False, color_category=color_category)
                else:
                    raise
        
        # Convert tensor to numpy array and reshape
        features = features.cpu().numpy().reshape(-1)
        
        # Memory cleanup
        del img_tensor
        if device.type == 'cuda':
            torch.cuda.empty_cache()
        
        logger.debug(f"Successfully extracted {len(features)} visual features")
        return features
        
    except Exception as e:
        logger.error(f"Feature extraction error: {str(e)}")
        if device.type == 'cuda' and use_gpu:
            logger.info("GPU error, falling back to CPU")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return extract_visual_features_resnet_fixed(image, remove_bg=False, use_gpu=False, color_category=color_category)
        else:
            # Return a zero vector as fallback
            logger.warning("Returning zero vector as fallback")
            return np.zeros(2048, dtype=np.float32)
        
def enhance_for_color_category(image, color_category):
    """
    Enhance image based on its color category for better feature extraction
    
    Args:
        image: PIL Image
        color_category: Color category string
        
    Returns:
        PIL Image: Enhanced image
    """
    try:
        img_array = np.array(image)
        
        if color_category in ['white', 'black']:
            # Enhance contrast for white/black products
            img_array = cv2.convertScaleAbs(img_array, alpha=1.2, beta=10)
        elif color_category in ['yellow', 'orange']:
            # Enhance for warm colors
            img_array = cv2.convertScaleAbs(img_array, alpha=1.1, beta=5)
        elif color_category in ['blue', 'green']:
            # Enhance for cool colors
            img_array = cv2.convertScaleAbs(img_array, alpha=1.05, beta=0)
        
        return Image.fromarray(img_array)
    except Exception as e:
        logger.warning(f"Color enhancement error: {str(e)}")
        return image

def get_text_embedding(text):
    """
    Generate basic text embedding using SentenceTransformer
    
    Args:
        text: Input text string
        
    Returns:
        numpy.ndarray: Text embedding vector
    """
    try:
        # Load model (cached after first use)
        model_key = 'sentence_transformer'
        if model_key not in _model_cache:
            logger.info("Loading SentenceTransformer model...")
            _model_cache[model_key] = SentenceTransformer('distiluse-base-multilingual-cased-v1')
        
        model = _model_cache[model_key]
        
        # Generate embedding
        embedding = model.encode(text)
        
        return embedding
        
    except Exception as e:
        logger.error(f"Text embedding error: {str(e)}")
        # Return a zero vector as fallback
        return np.zeros(512)  # distiluse-base-multilingual-cased-v1 has 512 dimensions

def get_color_aware_text_embedding(text, color_category):
    """
    Generate text embedding with color context
    
    Args:
        text: Product name/description
        color_category: Color category
        
    Returns:
        numpy.ndarray: Text embedding with color context
    """
    try:
        # Add color context to text
        if color_category != 'unknown' and color_category in COLOR_CATEGORIES:
            color_name = COLOR_CATEGORIES[color_category]['name']
            enhanced_text = f"{text} {color_name}"
        else:
            enhanced_text = text
        
        # Generate embedding
        return get_text_embedding(enhanced_text)
        
    except Exception as e:
        logger.error(f"Color-aware text embedding error: {str(e)}")
        return get_text_embedding(text)


def detect_edges(image):
    """
    Detect edges in image for analysis
    
    Args:
        image: PIL Image
        
    Returns:
        int: Number of edge pixels detected
    """
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to CV2 format
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Count edge pixels
        edge_count = np.sum(edges > 0)
        
        return edge_count
        
    except Exception as e:
        logger.warning(f"Edge detection error: {e}")
        return 0

def calculate_text_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two text embeddings
    
    Args:
        embedding1: First text embedding
        embedding2: Second text embedding
        
    Returns:
        float: Similarity score (0-1)
    """
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Ensure embeddings are numpy arrays and 2D
        emb1 = np.array(embedding1).reshape(1, -1)
        emb2 = np.array(embedding2).reshape(1, -1)
        
        # Calculate cosine similarity
        similarity = cosine_similarity(emb1, emb2)[0][0]
        
        # Ensure similarity is between 0 and 1
        return max(0.0, min(1.0, similarity))
        
    except Exception as e:
        logger.error(f"Text similarity calculation error: {str(e)}")
        return 0.0

class ColorAwareProductVectorIndex:
    """Enhanced FAISS index with color-based categorization"""
    
    def __init__(self):
        self.dimension = 2048  # ResNet50 feature vector size
        self.color_indices = {}  # Separate indices per color category
        self.product_metadata = {}  # Store product metadata including color info
        
        # Initialize indices for each color category
        for color in list(COLOR_CATEGORIES.keys()) + ['unknown']:
            self.color_indices[color] = {
                'index': faiss.IndexFlatL2(self.dimension),
                'product_ids': []
            }
    
    def add_product(self, product_id, feature_vector, color_category='unknown', metadata=None):
        """Add product to appropriate color-based index"""
        try:
            # Ensure vector has correct dimensions
            if len(feature_vector) != self.dimension:
                resized_vector = np.resize(feature_vector, (self.dimension,))
                feature_vector = resized_vector
            
            # Add to appropriate color index
            if color_category not in self.color_indices:
                color_category = 'unknown'
            
            color_index = self.color_indices[color_category]
            color_index['index'].add(np.array([feature_vector], dtype=np.float32))
            color_index['product_ids'].append(product_id)
            
            # Store metadata
            self.product_metadata[product_id] = {
                'color_category': color_category,
                'metadata': metadata or {}
            }
            
            logger.debug(f"Added product {product_id} to {color_category} index")
        except Exception as e:
            logger.error(f"Error adding product to index: {str(e)}")
    
    def search(self, feature_vector, color_category=None, k=5, search_similar_colors=True):
        """
        Search for similar products with color awareness
        
        Args:
            feature_vector: Feature vector to search
            color_category: Preferred color category
            k: Number of results
            search_similar_colors: Search in similar color categories too
            
        Returns:
            List of search results with metadata
        """
        try:
            # Ensure vector has correct dimensions
            if len(feature_vector) != self.dimension:
                resized_vector = np.resize(feature_vector, (self.dimension,))
                feature_vector = resized_vector
            
            all_results = []
            
            # Define search order
            if color_category and color_category in self.color_indices:
                search_categories = [color_category]
                
                if search_similar_colors:
                    # Add similar color categories
                    similar_colors = get_similar_color_categories(color_category)
                    search_categories.extend(similar_colors)
                    
                    # Add unknown category as fallback
                    if 'unknown' not in search_categories:
                        search_categories.append('unknown')
            else:
                # Search all categories
                search_categories = list(self.color_indices.keys())
            
            # Search in each category
            for category in search_categories:
                color_index = self.color_indices[category]
                
                if color_index['index'].ntotal == 0:
                    continue
                
                # Adjust k based on category priority
                if category == color_category:
                    category_k = min(k, color_index['index'].ntotal)
                else:
                    category_k = min(max(1, k // 3), color_index['index'].ntotal)
                
                distances, indices = color_index['index'].search(
                    np.array([feature_vector], dtype=np.float32), category_k
                )
                
                # Process results
                for idx, dist in zip(indices[0], distances[0]):
                    if idx != -1 and idx < len(color_index['product_ids']):
                        product_id = color_index['product_ids'][idx]
                        result = {
                            'product_id': product_id,
                            'distance': float(dist),
                            'color_category': category,
                            'is_exact_color_match': category == color_category,
                            'metadata': self.product_metadata.get(product_id, {})
                        }
                        all_results.append(result)
            
            # Sort by distance and color match preference
            all_results.sort(key=lambda x: (not x['is_exact_color_match'], x['distance']))
            
            return all_results[:k]
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []

def get_similar_color_categories(color_category):
    """Get similar color categories for expanded search"""
    similar_map = {
        'red': ['pink', 'orange'],
        'orange': ['red', 'yellow'],
        'yellow': ['orange', 'green'],
        'green': ['yellow', 'blue'],
        'blue': ['green', 'purple'],
        'purple': ['blue', 'pink'],
        'pink': ['red', 'purple'],
        'white': ['black'],
        'black': ['white'],
        'brown': ['orange', 'red'],
    }
    return similar_map.get(color_category, [])

# Singleton enhanced index
_enhanced_vector_index = None

def build_enhanced_vector_index():
    """
    Build the enhanced color-aware FAISS index
    """
    global _enhanced_vector_index
    
    try:
        from .models import Product
        
        logger.info("Building enhanced color-aware vector index...")
        
        # Create new enhanced index
        _enhanced_vector_index = ColorAwareProductVectorIndex()
        
        # Load all products with visual embeddings
        products = Product.objects.filter(visual_embedding__isnull=False)
        total_products = products.count()
        
        logger.info(f"Loading {total_products} products into enhanced index...")
        
        processed_count = 0
        for product in products:
            try:
                # Get color category from product metadata
                color_category = getattr(product, 'color_category', 'unknown')
                
                # Convert visual embedding to numpy array
                visual_features = np.array(product.visual_embedding, dtype=np.float32)
                
                # Add to enhanced index
                _enhanced_vector_index.add_product(
                    product.id,
                    visual_features,
                    color_category,
                    {
                        'name': product.name,
                        'brand': product.brand,
                        'category': product.category
                    }
                )
                processed_count += 1
                
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count}/{total_products} products")
                    
            except Exception as e:
                logger.warning(f"Error loading product {product.id}: {str(e)}")
                continue
        
        logger.info(f"Enhanced vector index built successfully with {processed_count} products")
        
        # Log color distribution
        color_stats = {}
        for color, color_index in _enhanced_vector_index.color_indices.items():
            count = color_index['index'].ntotal
            if count > 0:
                color_stats[color] = count
        
        logger.info(f"Color distribution: {color_stats}")
        
        return _enhanced_vector_index
        
    except Exception as e:
        logger.error(f"Error building enhanced vector index: {str(e)}")
        raise

def get_enhanced_vector_index():
    """Get or create the enhanced color-aware FAISS index"""
    global _enhanced_vector_index
    
    if _enhanced_vector_index is None:
        _enhanced_vector_index = build_enhanced_vector_index()
    
    return _enhanced_vector_index

def scan_barcode(image):
    """
    Scan barcode from image using pyzbar
    """
    try:
        import cv2
        import numpy as np
        from pyzbar.pyzbar import decode as decode_barcodes
        
        # Convert to CV2 format
        if isinstance(image, (bytes, io.BytesIO)):
            if isinstance(image, io.BytesIO):
                image = image.getvalue()
            nparr = np.frombuffer(image, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            img = np.array(image)
        
        # Decode barcodes
        barcodes = decode_barcodes(img)
        
        # Return first barcode if found
        if barcodes:
            return barcodes[0].data.decode('utf-8')
        
        return None
    except Exception as e:
        logger.error(f"Barcode scanning error: {e}")
        return None

def extract_text_from_image(image):
    """
    Extract text from image using OCR
    """
    try:
        # Simple OCR extraction (you can enhance this)
        import pytesseract
        
        if isinstance(image, Image.Image):
            text = pytesseract.image_to_string(image)
        else:
            # Convert to PIL Image
            pil_image = Image.open(image) if isinstance(image, (str, io.BytesIO)) else Image.fromarray(image)
            text = pytesseract.image_to_string(pil_image)
        
        return text.strip()
    except Exception as e:
        logger.error(f"OCR extraction error: {e}")
        return ""

def identify_product_enhanced(image, similarity_threshold=0.75):
    """
    Enhanced product identification with color-aware processing
    
    Args:
        image: Product image
        similarity_threshold: Similarity threshold (0-1)
        
    Returns:
        Product: Identified product or None
    """
    try:
        # Step 1: Analyze color category
        color_info = categorize_by_color(image)
        color_category = color_info['category']
        
        logger.info(f"Detected color category: {color_category} (confidence: {color_info['confidence']:.2f})")
        
        # Step 2: Extract visual features with color optimization
        vector_index = get_enhanced_vector_index()
        
        try:
            image_no_bg = remove_background(image)
            visual_features = extract_visual_features_resnet(
                image_no_bg, remove_bg=False, color_category=color_category
            )
        except Exception as e:
            logger.warning(f"Background removal failed: {str(e)}")
            visual_features = extract_visual_features_resnet(
                image, remove_bg=False, color_category=color_category
            )
        
        # Step 3: Search with color awareness
        candidates = vector_index.search(
            visual_features, 
            color_category=color_category, 
            k=10,
            search_similar_colors=True
        )
        
        if not candidates:
            # Fallback to barcode
            barcode = scan_barcode(image)
            if barcode:
                try:
                    from .models import Product
                    return Product.objects.get(barcode=barcode)
                except Product.DoesNotExist:
                    pass
            return None
        
        # Step 4: OCR and text analysis
        extracted_text = extract_text_from_image(image)
        text_embedding = get_color_aware_text_embedding(extracted_text, color_category)
        
        # Step 5: Score candidates
        scored_candidates = []
        from .models import Product
        
        for candidate in candidates:
            try:
                product = Product.objects.get(id=candidate['product_id'])
                
                # Visual similarity (with color bonus)
                visual_score = 1 - min(candidate['distance'] / 100.0, 1.0)
                if candidate['is_exact_color_match']:
                    visual_score *= 1.2  # Bonus for exact color match
                
                # Text similarity
                product_text_embedding = get_color_aware_text_embedding(product.name, color_category)
                text_similarity = calculate_text_similarity(text_embedding, product_text_embedding)
                
                # Combined score
                combined_score = 0.6 * visual_score + 0.4 * text_similarity
                
                scored_candidates.append({
                    'product': product,
                    'visual_score': visual_score,
                    'text_score': text_similarity,
                    'combined_score': combined_score,
                    'color_match': candidate['is_exact_color_match']
                })
            except Product.DoesNotExist:
                continue
        
        if not scored_candidates:
            return None
        
        # Sort by combined score
        scored_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
        best_match = scored_candidates[0]
        
        # Check threshold
        if best_match['combined_score'] > similarity_threshold:
            logger.info(f"Found match: {best_match['product'].name} (score: {best_match['combined_score']:.3f})")
            return best_match['product']
        
        # Final fallback to barcode
        barcode = scan_barcode(image)
        if barcode:
            try:
                return Product.objects.get(barcode=barcode)
            except Product.DoesNotExist:
                pass
        
        return None
        
    except Exception as e:
        logger.error(f"Enhanced product identification error: {str(e)}")
        return None

# Backward compatibility - keep original function names
def extract_visual_features(image, remove_bg=True, use_gpu=True):
    """Backward compatibility wrapper"""
    return extract_visual_features_resnet(image, remove_bg, use_gpu)

def identify_product(image, similarity_threshold=0.75):
    """Backward compatibility wrapper"""
    return identify_product_enhanced(image, similarity_threshold)

def get_vector_index():
    """Backward compatibility wrapper"""
    return get_enhanced_vector_index()

def build_vector_index():
    """Backward compatibility wrapper - calls the enhanced version"""
    return build_enhanced_vector_index()

# Remove the override function and keep only the enhanced versions
try:
    from .util_enhanced import (
        enhanced_product_preprocessing,
        extract_visual_features_enhanced,
        EnhancedProductDetector,
        intelligent_crop_product,
        safe_background_removal_v2
    )
    
    # Replace the aggressive background removal with enhanced preprocessing
    def smart_background_removal_enhanced(image):
        """Enhanced version that replaces the aggressive background removal"""
        try:
            processed_image, processing_info = enhanced_product_preprocessing(image, method='auto')
            
            # Convert to BytesIO for compatibility with existing code
            img_bytes = io.BytesIO()
            processed_image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Check if we had good detection
            detection_result = processing_info.get('detection_result')
            success = detection_result is not None and detection_result.get('confidence', 0) > 0.5
            
            return img_bytes, success
            
        except Exception as e:
            logger.error(f"Enhanced background removal failed: {e}")
            # Return original image
            original_bytes = io.BytesIO()
            image.save(original_bytes, format='PNG')
            original_bytes.seek(0)
            return original_bytes, False
    
    # Replace the ResNet feature extraction with enhanced version
    def extract_visual_features_resnet_enhanced(image, remove_bg=True, use_gpu=True, color_category=None):
        """Enhanced version that uses intelligent preprocessing"""
        try:
            if remove_bg:
                # Use enhanced preprocessing instead of aggressive background removal
                return extract_visual_features_enhanced(
                    image, 
                    preprocessing_method='auto',
                    use_gpu=use_gpu,
                    color_category=color_category
                )
            else:
                # Use original method for cases where no preprocessing is wanted
                return extract_visual_features_resnet(image, remove_bg=False, use_gpu=use_gpu, color_category=color_category)
        except Exception as e:
            logger.error(f"Enhanced feature extraction failed: {e}")
            # Fallback to original method
            return extract_visual_features_resnet(image, remove_bg=False, use_gpu=use_gpu, color_category=color_category)
    
    # Replace the product identification with enhanced version
    def identify_product_enhanced_v2(image, similarity_threshold=0.75):
        """Enhanced product identification with intelligent detection"""
        try:
            from .models import Product
            
            # Step 1: Enhanced preprocessing with product detection
            processed_image, processing_info = enhanced_product_preprocessing(image, method='auto')
            
            logger.info(f"Enhanced identification preprocessing: {processing_info['steps_applied']}")
            
            # Step 2: Color analysis
            color_info = categorize_by_color(processed_image)
            color_category = color_info['category']
            
            # Step 3: Extract visual features
            visual_features = extract_visual_features_resnet(
                processed_image,
                remove_bg=False,  # Already processed
                use_gpu=True,
                color_category=color_category
            )
            
            # Step 4: Search with enhanced vector index
            vector_index = get_enhanced_vector_index()
            candidates = vector_index.search(
                visual_features,
                color_category=color_category,
                k=10,
                search_similar_colors=True
            )
            
            if not candidates:
                # Fallback to barcode
                barcode = scan_barcode(processed_image)
                if barcode:
                    try:
                        return Product.objects.get(barcode=barcode)
                    except Product.DoesNotExist:
                        pass
                return None
            
            # Step 5: Enhanced scoring
            scored_candidates = []
            
            for candidate in candidates:
                try:
                    product = Product.objects.get(id=candidate['product_id'])
                    
                    # Visual similarity with detection bonus
                    visual_score = 1 - min(candidate['distance'] / 100.0, 1.0)
                    
                    # Bonus for exact color match
                    if candidate['is_exact_color_match']:
                        visual_score *= 1.2
                    
                    # Bonus if we had good product detection
                    detection_result = processing_info.get('detection_result')
                    if detection_result and detection_result.get('confidence', 0) > 0.7:
                        visual_score *= 1.15
                    
                    # Text similarity
                    try:
                        product_text_embedding = get_color_aware_text_embedding(product.name, color_category)
                        extracted_text = extract_text_from_image(processed_image)
                        if extracted_text.strip():
                            query_text_embedding = get_color_aware_text_embedding(extracted_text, color_category)
                            text_similarity = calculate_text_similarity(query_text_embedding, product_text_embedding)
                        else:
                            text_similarity = 0.5
                    except:
                        text_similarity = 0.5
                    
                    # Combined score with enhanced weighting
                    if detection_result:
                        # If we detected the product well, rely more on visual features
                        combined_score = 0.75 * visual_score + 0.25 * text_similarity
                    else:
                        # Standard weighting
                        combined_score = 0.6 * visual_score + 0.4 * text_similarity
                    
                    scored_candidates.append({
                        'product': product,
                        'combined_score': combined_score,
                        'visual_score': visual_score,
                        'text_score': text_similarity
                    })
                    
                except Product.DoesNotExist:
                    continue
            
            if not scored_candidates:
                return None
            
            # Sort by combined score
            scored_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
            best_match = scored_candidates[0]
            
            # Check threshold
            if best_match['combined_score'] > similarity_threshold:
                logger.info(f"Enhanced match found: {best_match['product'].name} (score: {best_match['combined_score']:.3f})")
                return best_match['product']
            
            return None
            
        except Exception as e:
            logger.error(f"Enhanced product identification error: {str(e)}")
            return None
    
    # Override the existing functions with enhanced versions
    smart_background_removal = smart_background_removal_enhanced
    extract_visual_features_resnet = extract_visual_features_resnet_enhanced
    identify_product_enhanced = identify_product_enhanced_v2
    
    logger.info("✅ Enhanced detection functions integrated successfully")
    
except ImportError as e:
    logger.warning(f"Enhanced detection not available: {e}")
    logger.info("Using original detection methods")
except Exception as e:
    logger.error(f"Failed to integrate enhanced detection: {e}")
    logger.info("Using original detection methods")




def safe_conservative_crop(image, max_crop_factor=0.85):
    """Quick fix for over-aggressive cropping"""
    width, height = image.size
    
    # Never crop more than 15% from any side
    margin_x = int(width * (1 - max_crop_factor) / 2)
    margin_y = int(height * (1 - max_crop_factor) / 2)
    
    x1, y1 = margin_x, margin_y
    x2, y2 = width - margin_x, height - margin_y
    
    return image.crop((x1, y1, x2, y2))