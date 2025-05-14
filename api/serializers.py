from django.contrib.auth.models import User
from rest_framework import serializers

from .util import extract_visual_features, get_text_embedding
from .models import Product, Store, Price
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
        # Check if passwords match
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords don't match"})
        
        # Check password strength
        if len(data['password']) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long"})
            
        return data
    
    def create(self, validated_data):
        # Remove password_confirm from validated data
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


# İlave olarak, ürün tanıma için özel serileştiriciler
class ProductIdentificationSerializer(serializers.Serializer):
    image = serializers.ImageField()
    store_id = serializers.IntegerField(required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)

# Add to serializers.py - Enhanced Product Serializers

class ProductBarcodeSerializer(serializers.Serializer):
    """Serializer for adding products via barcode"""
    barcode = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    weight = serializers.CharField(max_length=50, required=False, allow_blank=True)
    image = serializers.ImageField(required=False)

class ProductCreationSerializer(serializers.ModelSerializer):
    """Serializer for creating new products"""
    image = serializers.ImageField(required=False)
    
    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'brand', 'category', 
            'weight', 'ingredients', 'image'
        ]
    
    def create(self, validated_data):
        # Handle image upload if present
        image = validated_data.pop('image', None)
        
        # Create product
        product = Product.objects.create(**validated_data)
        
        # Process image if provided
        if image:
            # For a real app, upload to cloud storage and store URL
            # product.image_url = uploaded_url
            
            # Extract visual features
            try:
                visual_features = extract_visual_features(image)
                product.visual_embedding = visual_features.tolist()
            except Exception as e:
                print(f"Error extracting visual features: {e}")
        
        # Generate text embedding
        try:
            text_embedding = get_text_embedding(product.name)
            product.text_embedding = text_embedding.tolist()
            product.save()
        except Exception as e:
            print(f"Error generating text embedding: {e}")
        
        return product

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'latitude', 'longitude', 'address']

class ProductSerializer(serializers.ModelSerializer):
    # Get lowest price information (optional)
    lowest_price = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'brand', 'category', 
            'image_url', 'image_front_url', 'image_ingredients_url',
            'weight', 'ingredients', 'created_at', 'updated_at',
            'lowest_price'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
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

class PriceSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Price
        fields = [
            'id', 'product', 'product_name', 'store', 'store_name', 
            'price', 'user', 'username', 'created_at'
        ]
        read_only_fields = ['created_at', 'user', 'username']