# api/views.py dosyasını açın ve importları düzeltin:
from django.shortcuts import render
from django.db import models
from django.db.models.expressions import RawSQL
from django.db.models import Min, Count, F
from django.utils import timezone
from datetime import timedelta

from rest_framework import viewsets, status, permissions  # permissions ekleyin!
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import Product, Store, Price
from .util import get_vector_index, identify_product, get_text_embedding

from django.shortcuts import get_object_or_404

from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Product, Store, Price
from .serializers import (
    ProductSerializer, PriceSerializer, StoreSerializer,
    ProductCreationSerializer, ProductBarcodeSerializer
)
from .util import identify_product, extract_visual_features, scan_barcode, get_text_embedding

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    # Existing methods remain...
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @parser_classes([MultiPartParser, FormParser])
    def add_from_barcode(self, request):
        """
        Add product from barcode information.
        Expects barcode, name, and optionally other product details
        """
        serializer = ProductBarcodeSerializer(data=request.data)
        
        if serializer.is_valid():
            barcode = serializer.validated_data['barcode']
            
            # Check if product already exists
            try:
                product = Product.objects.get(barcode=barcode)
                return Response({
                    'detail': 'Product with this barcode already exists',
                    'product': ProductSerializer(product).data
                }, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                # Create new product from barcode data
                product_data = {
                    'name': serializer.validated_data['name'],
                    'barcode': barcode,
                    'brand': serializer.validated_data.get('brand', ''),
                    'category': serializer.validated_data.get('category', ''),
                    'weight': serializer.validated_data.get('weight', ''),
                }
                
                # Process image if provided
                image = request.FILES.get('image')
                if image:
                    # Save image to cloud storage or your media location and get URL
                    # For simplicity, we're assuming image handling happens elsewhere
                    # and we're just storing the URL
                    product_data['image_url'] = "placeholder_url"  # Replace with actual URL
                    
                    # Extract visual features if possible
                    try:
                        visual_features = extract_visual_features(image)
                        product_data['visual_embedding'] = visual_features.tolist()
                    except Exception as e:
                        # Log the error but continue
                        print(f"Error extracting visual features: {e}")
                
                # Generate text embedding
                try:
                    text_embedding = get_text_embedding(product_data['name'])
                    product_data['text_embedding'] = text_embedding.tolist()
                except Exception as e:
                    # Log the error but continue
                    print(f"Error generating text embedding: {e}")
                
                # Create product
                product = Product.objects.create(**product_data)
                
                return Response({
                    'detail': 'Product created successfully',
                    'product': ProductSerializer(product).data
                }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @parser_classes([MultiPartParser, FormParser])
    def scan_barcode(self, request):
        """
        Scan barcode from image and find or create product
        """
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'Image required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Scan barcode from image
            barcode = scan_barcode(image)
            
            if not barcode:
                return Response({'found': False, 'detail': 'No barcode detected in image'}, 
                                status=status.HTTP_404_NOT_FOUND)
            
            # Check if product exists with this barcode
            try:
                product = Product.objects.get(barcode=barcode)
                return Response({
                    'found': True,
                    'product': ProductSerializer(product).data,
                    'barcode': barcode
                })
            except Product.DoesNotExist:
                # Product doesn't exist yet
                return Response({
                    'found': False,
                    'barcode': barcode,
                    'detail': 'Product not found, but barcode scanned successfully'
                })
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        """
        Find product by barcode
        """
        barcode = request.query_params.get('barcode', '')
        if not barcode:
            return Response({'error': 'Barcode parameter required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(barcode=barcode)
            return Response({
                'found': True,  
                'product': ProductSerializer(product).data
            })
        except Product.DoesNotExist:
            return Response({
                'found': False,
                'barcode': barcode
            }, status=status.HTTP_404_NOT_FOUND)

class PriceViewSet(viewsets.ModelViewSet):
    queryset = Price.objects.all()
    serializer_class = PriceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        """Automatically set the user when creating a price entry"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def add_price(self, request):
        """
        Add new price for a product at a store
        """
        product_id = request.data.get('product')
        store_id = request.data.get('store')
        price = request.data.get('price')
        
        if not all([product_id, store_id, price]):
            return Response({'error': 'Product, store, and price are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get product and store
            product = Product.objects.get(pk=product_id)
            store = Store.objects.get(pk=store_id)
            
            # Create price entry
            price_obj = Price.objects.create(
                product=product,
                store=store,
                price=price,
                user=request.user
            )
            
            return Response({
                'detail': 'Price added successfully',
                'price': PriceSerializer(price_obj).data
            }, status=status.HTTP_201_CREATED)
            
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Haversine formülü ile iki nokta arası mesafeyi hesaplar (km cinsinden)
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Dünya yarıçapı (km)
    
    # Radyana dönüştür
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formülü
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance



class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

# api/views.py içine ekleyin
@api_view(['GET'])
def test_visual_index(request):
    """Görsel index'in çalışıp çalışmadığını test et"""
    try:
        index = get_vector_index()
        return Response({
            'status': 'success',
            'index_size': index.index.ntotal,
            'product_count': len(index.product_ids)
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)