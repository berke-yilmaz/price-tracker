# api/serializers.py - FINAL VERSION with ProductCreationSerializer and fixed imports
from django.contrib.auth.models import User
from rest_framework import serializers
from .util import (
    extract_visual_features_resnet, 
    get_color_aware_text_embedding,
    categorize_by_color
)
from .models import Product, Store, Price, ProcessingJob
from django.contrib.auth import authenticate
from django.utils import timezone
import random
import time

# Fix PIL import warnings
try:
    from PIL import Image as PILImage
except ImportError:
    import PIL.Image as PILImage

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords don't match"})
        
        if len(data['password']) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long"})
            
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    confirm_new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value
    
    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "New passwords don't match"})
        
        if len(data['new_password']) < 8:
            raise serializers.ValidationError({"new_password": "Password must be at least 8 characters long"})
            
        return data

# Enhanced Product Serializers with Image Display

class ProductSerializer(serializers.ModelSerializer):
    """
    This serializer now correctly handles price display by prioritizing
    the efficient 'lowest_price_val' annotation from the view.
    """
    # ⭐ --- START OF FIX --- ⭐
    lowest_price = serializers.SerializerMethodField()
    image_display_url = serializers.CharField(source='get_image_url', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'brand', 'category', 
            'image', 'image_url', 'image_front_url', 'image_display_url',
            'weight', 'ingredients',
            'color_category', 'color_confidence', 'dominant_colors',
            'processing_status', 'created_at', 'updated_at', 'processed_at',
            'lowest_price' # We only need this one field now
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'processed_at', 'processing_status',
            'color_category', 'color_confidence', 'dominant_colors'
        ]
    
    def get_lowest_price(self, obj):
        """
        This method is now robust. It checks for the pre-calculated 'lowest_price_val'
        from the optimized queryset first. This makes the Search screen fast.
        If that's not present, it falls back to a direct query.
        """
        if hasattr(obj, 'lowest_price_val') and obj.lowest_price_val is not None:
            # The view provided the price, so we just return it.
            return {'price': obj.lowest_price_val}
        
        # Fallback for other contexts (like the History screen's nested product)
        price_instance = Price.objects.filter(product=obj).order_by('price').first()
        if price_instance:
            return {'price': price_instance.price, 'store': price_instance.store.name}
        
        return None
    # ⭐ --- END OF FIX --- ⭐
class ProductCreationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating products. This version is now correct.
    """
    image = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'brand', 'category', 
            'weight', 'ingredients', 'image'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        from .tasks import process_product_image

        image = validated_data.pop('image', None)
        validated_data['processing_status'] = 'pending'
        
        if not validated_data.get('barcode'):
            validated_data['barcode'] = f"AI-{int(time.time())}{random.randint(100, 999)}"
        
        product = Product.objects.create(**validated_data)
        
        if image:
            product.image.save(f"product_{product.id}.jpg", image, save=True)
            process_product_image.delay(product.id)
            
        return product

    
    def _process_product_image(self, product, image):
        """Process uploaded image for color and visual features"""
        try:
            import io
            
            # Convert to PIL Image with proper handling
            if hasattr(image, 'read'):
                image.seek(0)  # Reset file pointer
                img_data = image.read()
                pil_image = PILImage.open(io.BytesIO(img_data)).convert('RGB')
            else:
                pil_image = PILImage.open(image).convert('RGB')
            
            # Color analysis
            color_info = categorize_by_color(pil_image)
            product.color_category = color_info['category']
            product.color_confidence = float(color_info['confidence'])

            if color_info.get('colors'):
                product.dominant_colors = color_info['colors']
            
            # Visual features extraction with ResNet
            try:
                visual_features = extract_visual_features_resnet(
                    pil_image, 
                    color_category=color_info['category']
                )
                product.visual_embedding = visual_features.tolist()
            except Exception as e:
                print(f"Error extracting visual features: {e}")
            
            # Update processing status
            product.processing_status = 'completed'
            product.processed_at = timezone.now()
            product.save()
            
        except Exception as e:
            print(f"Error processing product image: {e}")
            product.processing_status = 'failed'
            product.processing_error = str(e)
            product.save()

class ProductBarcodeSerializer(serializers.Serializer):
    """Enhanced serializer for adding products via barcode with color processing"""
    barcode = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    weight = serializers.CharField(max_length=50, required=False, allow_blank=True)
    ingredients = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)
    auto_process = serializers.BooleanField(default=True)
    
    def create(self, validated_data):
        """Create product from barcode data"""
        image = validated_data.pop('image', None)
        auto_process = validated_data.pop('auto_process', True)
        
        # Use ProductCreationSerializer for actual creation
        serializer = ProductCreationSerializer(data=validated_data)
        if serializer.is_valid():
            product = serializer.save()
            
            # Handle image separately if provided
            if image and auto_process:
                serializer._process_product_image(product, image)
            
            return product
        else:
            raise serializers.ValidationError(serializer.errors)

class ProductIdentificationSerializer(serializers.Serializer):
    """Enhanced serializer for product identification with color hints"""
    image = serializers.ImageField()
    store_id = serializers.IntegerField(required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    color_hint = serializers.ChoiceField(
        choices=Product.COLOR_CHOICES,
        required=False,
        help_text="Optional color hint to improve identification"
    )

class ProductSearchSerializer(serializers.Serializer):
    """Enhanced search serializer with color filtering"""
    query = serializers.CharField(required=False, allow_blank=True)
    color_category = serializers.ChoiceField(
        choices=Product.COLOR_CHOICES,
        required=False,
        help_text="Filter by color category"
    )
    brand = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    min_confidence = serializers.FloatField(
        required=False, 
        min_value=0.0, 
        max_value=1.0,
        help_text="Minimum color confidence score"
    )
    has_visual_features = serializers.BooleanField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)

# api/serializers.py - Enhanced Store serializer
class StoreSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField(read_only=True)
    distance = serializers.SerializerMethodField(read_only=True)
    distance_text = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'latitude', 'longitude', 'address',
            'formatted_address', 'city', 'country', 'postal_code',
            'phone', 'website', 'opening_hours',
            'product_count', 'distance', 'distance_text',
            'created_at'
        ]
    
    def get_product_count(self, obj):
        return Price.objects.filter(store=obj).values('product').distinct().count()
    
    def get_distance(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user_location') and obj.has_location:
            user_lat = request.user_location.get('latitude')
            user_lng = request.user_location.get('longitude')
            if user_lat and user_lng:
                return obj.calculate_distance(user_lat, user_lng)
        return None
    
    def get_distance_text(self, obj):
        distance = self.get_distance(obj)
        if distance is not None:
            if distance < 1:
                return f"{int(distance * 1000)}m"
            else:
                return f"{distance:.1f}km"
        return None

class StoreCreationSerializer(serializers.ModelSerializer):
    """Serializer for creating new stores with location support"""
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'address', 'latitude', 'longitude']
        read_only_fields = ['id']
    
    def validate_name(self, value):
        """Ensure store name is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Store name cannot be empty")
        return value.strip()
    
    def create(self, validated_data):
        """Create store with validation"""
        # Check for duplicate stores at the same location
        if validated_data.get('latitude') and validated_data.get('longitude'):
            existing_store = Store.objects.filter(
                name=validated_data['name'],
                latitude=validated_data['latitude'],
                longitude=validated_data['longitude']
            ).first()
            
            if existing_store:
                raise serializers.ValidationError("A store with this name already exists at this location")
        
        return Store.objects.create(**validated_data)

class PriceSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    # We no longer need a separate product_name, as it will be inside the 'product' object.
    # product_name = serializers.CharField(source='product.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    # ⭐ THE KEY FIX IS HERE ⭐
    # This tells DRF to use the ProductSerializer to create a full nested object
    # for the 'product' field, instead of just its ID.
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Price
        fields = [
            'id', 
            'product',        # This will now be the full product object
            'store', 
            'store_name', 
            'price', 
            'user', 
            'username', 
            'created_at', 
            'date'
        ]
        read_only_fields = ['created_at', 'user', 'username']
    
    def validate_price(self, value):
        """Ensure price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero")
        return value

# ⭐ --- START OF FIX --- ⭐
class PriceCreationSerializer(serializers.ModelSerializer):
    """
    This serializer is specifically for CREATING a new price.
    It correctly accepts the primary keys (IDs) for product and store.
    """
    # We expect the frontend to send the ID for the product and store.
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())

    class Meta:
        model = Price
        fields = ['product', 'store', 'price', 'date']

    def create(self, validated_data):
        # Associate the price with the currently logged-in user.
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        # Check for existing price to prevent duplicates
        # This is better done here than with a UniqueConstraint for a friendlier error.
        existing_price = Price.objects.filter(
            product=validated_data['product'],
            store=validated_data['store'],
            date=validated_data.get('date', timezone.now().date())
        ).first()

        if existing_price:
            raise serializers.ValidationError({
                'non_field_errors': ['A price for this product at this store has already been added today.']
            })
            
        return Price.objects.create(**validated_data)
# ⭐ --- END OF FIX --- ⭐

class ProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for monitoring processing jobs"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    processing_time = serializers.FloatField(read_only=True)
    can_retry = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ProcessingJob
        fields = [
            'id', 'product', 'product_name', 'job_type', 'status',
            'created_at', 'started_at', 'completed_at', 'processing_time',
            'result_data', 'error_message', 'priority', 'retry_count',
            'max_retries', 'can_retry'
        ]
        read_only_fields = [
            'created_at', 'started_at', 'completed_at', 'processing_time',
            'result_data', 'can_retry'
        ]