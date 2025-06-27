# debug_preprocessor.py - Run this to find the exact issue
import os
import sys
import django

# Setup Django
sys.path.append('/home/berke/Desktop/Price Tracker/PriceTracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PriceTracker.settings')
django.setup()

# Now test the preprocessor
from api.enhanced_preprocessor import EnhancedProductPreprocessor
from PIL import Image
import io
import numpy as np

def test_preprocessor():
    """Test the preprocessor with a simple image to find the exact error location"""
    
    # Create a simple test image
    test_image = Image.new('RGB', (100, 100), color='red')
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='JPEG')
    image_bytes = img_bytes.getvalue()
    
    print("Creating preprocessor...")
    try:
        preprocessor = EnhancedProductPreprocessor(target_size=(256, 256), use_gpu=False)
        print("✅ Preprocessor created successfully")
    except Exception as e:
        print(f"❌ Failed to create preprocessor: {e}")
        return
    
    print("Processing test image...")
    try:
        results = preprocessor.process_image(image_bytes, return_steps=True)
        if results['success']:
            print("✅ Processing successful!")
            print(f"Steps completed: {results['processing_steps']}")
            print(f"Warnings: {results.get('warnings', [])}")
        else:
            print(f"❌ Processing failed: {results.get('error')}")
    except Exception as e:
        print(f"❌ Processing exception: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_preprocessor()