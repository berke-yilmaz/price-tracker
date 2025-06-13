# api/serializers.py - Enhanced with Color Support
from django.contrib.auth.models import User
from rest_framework import serializers
from .util import (
    extract_visual_features_resnet, 
    get_color_aware_text_embedding,
    categorize_by_color
)
from .models import Product, Store, Price, ProcessingJob
from django.contrib.auth import authenticate

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

# Enhanced Product Serializers with Color Support

class ProductColorInfoSerializer(serializers.Serializer):
    """Serializer for color information"""
    category = serializers.CharField()
    confidence = serializers.FloatField()
    dominant_colors = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField())
    )
    color_display = serializers.CharField()

class ProductSerializer(serializers.ModelSerializer):
    """Enhanced Product serializer with color information"""
    lowest_price = serializers.SerializerMethodField(read_only=True)
    color_info = serializers.SerializerMethodField(read_only=True)
    color_display = serializers.CharField(source='get_color_display', read_only=True)
    is_processed = serializers.BooleanField(read_only=True)
    has_visual_features = serializers.BooleanField(read_only=True)
    has_color_analysis = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'brand', 'category', 
            'image_url', 'image_front_url', 'weight', 'ingredients',
            'color_category', 'color_confidence', 'color_display', 'dominant_colors',
            'processing_status', 'created_at', 'updated_at', 'processed_at',
            'lowest_price', 'color_info', 'is_processed', 
            'has_visual_features', 'has_color_analysis'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'processed_at', 'processing_status',
            'color_category', 'color_confidence', 'dominant_colors'
        ]
    
    def get_lowest_price(self, obj):
        """Return the lowest price"""
        price = Price.objects.filter(product=obj).order_by('price').first()
        if price:
            return {
                'price': price.price,
                'store': price.store.name,
                'date': price.created_at
            }
        return None
    
    def get_color_info(self, obj):
        """Return detailed color information"""
        if obj.has_color_analysis:
            return {
                'category': obj.color_category,
                'confidence': obj.color_confidence,
                'display_name': obj.get_color_display(),
                'dominant_colors': obj.dominant_colors or [],
                'has_analysis': True
            }
        return {
            'category': 'unknown',
            'confidence': 0.0,
            'display_name': 'Belirsiz',
            'dominant_colors': [],
            'has_analysis': False
        }

class ProductCreationSerializer(serializers.ModelSerializer):
    """Enhanced serializer for creating new products with automatic processing"""
    image = serializers.ImageField(required=False, write_only=True)
    auto_process = serializers.BooleanField(default=True, write_only=True)
    
    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'brand', 'category', 
            'weight', 'ingredients', 'image', 'auto_process'
        ]
    
    def create(self, validated_data):
        image = validated_data.pop('image', None)
        auto_process = validated_data.pop('auto_process', True)
        
        # Create product
        product = Product.objects.create(**validated_data)
        
        # Process image if provided
        if image and auto_process:
            self._process_product_image(product, image)
        
        # Generate text embedding
        if auto_process:
            try:
                # Use color-aware text embedding if color is known
                color_category = getattr(product, 'color_category', 'unknown')
                text_embedding = get_color_aware_text_embedding(product.name, color_category)
                product.color_aware_text_embedding = text_embedding.tolist()
                product.save()
            except Exception as e:
                print(f"Error generating text embedding: {e}")
        
        return product
    
    def _process_product_image(self, product, image):
        """Process uploaded image for color and visual features"""
        try:
            from PIL import Image as PILImage
            import io
            
            # Convert to PIL Image
            if hasattr(image, 'read'):
                img_data = image.read()
                pil_image = PILImage.open(io.BytesIO(img_data)).convert('RGB')
            else:
                pil_image = PILImage.open(image).convert('RGB')
            
            # Color analysis
            color_info = categorize_by_color(pil_image)
            product.color_category = color_info['category']
            product.color_confidence = float(color_info['confidence'])

            if color_info['colors']:
                product.dominant_colors = color_info['colors']
            
            # Visual features extraction with ResNet
            try:
                visual_features = extract_visual_features_resnet(
                    pil_image, 
                    remove_bg=True,
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
    image = serializers.ImageField(required=False)
    auto_process = serializers.BooleanField(default=True)

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

class StoreSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'latitude', 'longitude', 'address', 'product_count']
    
    def get_product_count(self, obj):
        """Return number of products with prices in this store"""
        return Price.objects.filter(store=obj).values('product').distinct().count()

class PriceSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_color = serializers.CharField(source='product.get_color_display', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Price
        fields = [
            'id', 'product', 'product_name', 'product_color',
            'store', 'store_name', 'price', 'user', 'username', 
            'created_at', 'date'
        ]
        read_only_fields = ['created_at', 'user', 'username']

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

class ColorAnalysisSerializer(serializers.Serializer):
    """Serializer for color analysis results"""
    image = serializers.ImageField(write_only=True)
    category = serializers.CharField(read_only=True)
    confidence = serializers.FloatField(read_only=True)
    dominant_colors = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField()),
        read_only=True
    )
    color_votes = serializers.DictField(read_only=True)
    display_name = serializers.CharField(read_only=True)

class ProductColorStatsSerializer(serializers.Serializer):
    """Serializer for color category statistics"""
    color_category = serializers.CharField()
    display_name = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()
    avg_confidence = serializers.FloatField()

class ProductSimilaritySerializer(serializers.Serializer):
    """Serializer for product similarity search results"""
    query_image = serializers.ImageField(write_only=True)
    color_filter = serializers.ChoiceField(
        choices=Product.COLOR_CHOICES,
        required=False,
        help_text="Filter results by color category"
    )
    max_results = serializers.IntegerField(default=10, min_value=1, max_value=50)
    include_similar_colors = serializers.BooleanField(default=True)
    
    # Read-only result fields
    results = ProductSerializer(many=True, read_only=True)
    query_color_info = serializers.DictField(read_only=True)
    processing_time = serializers.FloatField(read_only=True)

class BulkProductProcessingSerializer(serializers.Serializer):
    """Serializer for bulk product processing requests"""
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        max_length=100,
        help_text="List of product IDs to process"
    )
    job_types = serializers.MultipleChoiceField(
        choices=ProcessingJob.JOB_TYPES,
        default=['color_analysis', 'visual_features'],
        help_text="Types of processing to perform"
    )
    priority = serializers.IntegerField(default=0, help_text="Job priority")
    force_reprocess = serializers.BooleanField(
        default=False,
        help_text="Reprocess even if already completed"
    )

# Enhanced views integration serializers
class ProductRecommendationSerializer(serializers.Serializer):
    """Serializer for product recommendations based on color and features"""
    source_product_id = serializers.IntegerField()
    max_recommendations = serializers.IntegerField(default=5, min_value=1, max_value=20)
    color_weight = serializers.FloatField(
        default=0.3, 
        min_value=0.0, 
        max_value=1.0,
        help_text="Weight of color similarity in recommendations"
    )
    visual_weight = serializers.FloatField(
        default=0.5,
        min_value=0.0,
        max_value=1.0,
        help_text="Weight of visual similarity in recommendations"
    )
    text_weight = serializers.FloatField(
        default=0.2,
        min_value=0.0,
        max_value=1.0,
        help_text="Weight of text similarity in recommendations"
    )
    
    def validate(self, data):
        """Ensure weights sum to 1.0"""
        total_weight = data['color_weight'] + data['visual_weight'] + data['text_weight']
        if abs(total_weight - 1.0) > 0.01:
            raise serializers.ValidationError(
                "Color, visual, and text weights must sum to 1.0"
            )
        return data