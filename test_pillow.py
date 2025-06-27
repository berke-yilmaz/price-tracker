# Create this file: test_pillow.py in your project root

from PIL import Image

def test_pillow_compatibility():
    """Test Pillow version compatibility"""
    try:
        # Test old way
        print("Testing Image.ANTIALIAS...")
        test = Image.ANTIALIAS
        print("✅ Image.ANTIALIAS works")
    except AttributeError:
        print("❌ Image.ANTIALIAS not available (Pillow 10.0+)")
        
    try:
        # Test new way
        print("Testing Image.Resampling.LANCZOS...")
        test = Image.Resampling.LANCZOS
        print("✅ Image.Resampling.LANCZOS works")
    except AttributeError:
        print("❌ Image.Resampling.LANCZOS not available (Pillow < 10.0)")
    
    # Check Pillow version
    import PIL
    print(f"📦 Pillow version: {PIL.__version__}")

if __name__ == "__main__":
    test_pillow_compatibility()