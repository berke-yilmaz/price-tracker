import random
from django.shortcuts import get_object_or_404
from django.db.models import Min, Count, Q, Avg
from django.utils import timezone
from django.db import transaction
import time
import numpy as np
import io
from thefuzz import fuzz
import json # <--- ADD THIS IMPORT
from rest_framework import viewsets, status, permissions, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
import json # <-- Added this back in, as it's needed in get_visual_search_result
from django.db.models import Count, F, ExpressionWrapper, FloatField
from django.db.models.functions import Radians, Cos, Sin, ASin, Sqrt
import logging
logger = logging.getLogger(__name__)
from django.db.models import Min, Count, Q, Avg, Subquery, OuterRef, F, ExpressionWrapper, FloatField
from django.db.models.functions import Radians, Cos, Sin, ASin, Sqrt
# --- Import local modules ---
from .models import Product, Store, Price, VisualSearchJob
from .serializers import (
    ProductCreationSerializer, ProductSerializer, PriceSerializer, StoreSerializer,
    ProductBarcodeSerializer, ProductIdentificationSerializer, ProductSearchSerializer, PriceCreationSerializer
)
from .util import (
    categorize_by_color,
    extract_product_info_from_text,
    extract_text_from_product_image,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    get_vector_index,
    identify_product,
    build_vector_index # <-- Added this import
)
from .tasks import process_product_image, perform_visual_search
from .redis import get_cached_product, cache_product

try:
    from PIL import Image as PILImage
except ImportError:
    import PIL.Image as PILImage

try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    print("Google Cloud Vision not available - OCR features will be limited")

class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class EnhancedProductPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        # ⭐ FIX: Add the new 'prices' action to the list of allowed read-only actions
        if view.action in ['list', 'retrieve', 'search', 'by_barcode', 'gallery', 'similar', 'color_stats', 'find_similar_by_image', 'prices']:
            return True
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # ⭐ FIX: Also add 'prices' here to allow access to a specific product's prices
        if view.action in ['retrieve', 'similar', 'prices']:
            return True
        if request.user.is_superuser:
            return True
        if view.action in ['update', 'partial_update', 'destroy']:
            return request.user and request.user.is_authenticated
        return False
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [EnhancedProductPermissions]
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'brand', 'barcode', 'category']
    ordering_fields = ['created_at', 'name', 'brand', 'color_confidence', 'lowest_price_val', 'nearest_distance_km']
    ordering = ['-created_at']




    def get_queryset(self):
        """
        ⭐ --- START OF FIX 1 --- ⭐
        This is the new, robust queryset for products. It reliably annotates
        the single lowest price for every product.
        """
        queryset = Product.objects.all()

        # Create a subquery to find the minimum price for each product.
        lowest_price_subquery = Price.objects.filter(
            product=OuterRef('pk')
        ).order_by('price').values('price')[:1]
        
        # Annotate the main queryset with this value.
        queryset = queryset.annotate(
            lowest_price_val=Subquery(lowest_price_subquery)
        )

        # Apply standard filtering
        if search := self.request.query_params.get('search'):
            queryset = queryset.filter(Q(name__icontains=search) | Q(brand__icontains=search))
        
        # Apply ordering - this can now safely use 'lowest_price_val'
        ordering = self.request.query_params.get('ordering', '-created_at')
        if ordering.lstrip('-') in self.ordering_fields:
            queryset = queryset.order_by(ordering)
            
        return queryset.distinct()
        # ⭐ --- END OF FIX 1 --- ⭐
    
    def destroy(self, request, *args, **kwargs):
        """Enhanced delete with cascade handling and logging"""
        instance = self.get_object()
        
        try:
            with transaction.atomic():
                logger.info(f"User {request.user.username} is deleting product: {instance.name} (ID: {instance.id})")
                
                price_count = Price.objects.filter(product=instance).count()
                
                instance.delete()
                
                logger.info(f"Successfully deleted product {instance.id} and {price_count} related prices")
                
                try:
                    if instance.visual_embedding:
                        from .util import build_vector_index
                        build_vector_index()
                        logger.info("Vector index updated after product deletion")
                except Exception as e:
                    logger.warning(f"Failed to update vector index after deletion: {e}")
                
                return Response({
                    'detail': 'Product deleted successfully',
                    'deleted_prices': price_count
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error deleting product {instance.id}: {str(e)}")
            return Response({
                'detail': 'Failed to delete product',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def force_delete(self, request, pk=None):
        """Force delete a product with all related data"""
        product = self.get_object()
        
        try:
            with transaction.atomic():
                price_count = Price.objects.filter(product=product).count()
                Price.objects.filter(product=product).delete()
                
                product_name = product.name
                product.delete()
                
                logger.info(f"Force deleted product '{product_name}' and {price_count} prices by user {request.user.username}")
                
                return Response({
                    'detail': f'Product "{product_name}" and {price_count} related prices have been permanently deleted',
                    'deleted_prices': price_count
                })
                
        except Exception as e:
            logger.error(f"Force delete failed for product {pk}: {str(e)}")
            return Response({
                'detail': 'Force delete failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def deletion_stats(self, request):
        """Get statistics about products that can be deleted"""
        user = request.user
        
        if not user.is_authenticated:
            return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        total_products = Product.objects.count()
        products_with_no_prices = Product.objects.filter(prices__isnull=True).count()
        
        return Response({
            'total_products': total_products,
            'products_with_prices': total_products - products_with_no_prices,
            'products_without_prices': products_with_no_prices,
            'user_can_delete': total_products,
            'deletion_permissions': {
                'can_delete_any': user.is_superuser,
                'can_delete_own': user.is_authenticated,
                'can_force_delete': user.is_superuser
            }
        })
    
    def list(self, request, *args, **kwargs):
        """Enhanced list method with search debugging"""
        search_params = {k: v for k, v in request.query_params.items() if v}
        
        if search_params:
            logger.info(f"Product search with parameters: {search_params}")
        
        queryset = self.filter_queryset(self.get_queryset())
        total_count = queryset.count()
        
        if search_params:
            logger.info(f"Search returned {total_count} total products from database")
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            
            if search_params and hasattr(result, 'data'):
                result.data['search_debug'] = {
                    'search_params': search_params,
                    'total_results': total_count,
                    'page_size': len(page),
                    'total_products_in_db': Product.objects.count(),
                    'can_delete': request.user.is_authenticated
                }
            
            return result

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Dedicated search endpoint with enhanced functionality"""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({'results': [], 'count': 0, 'message': 'No search query provided'})
        
        search_q = (
            Q(name__icontains=query) | Q(brand__icontains=query) |
            Q(barcode__icontains=query) | Q(category__icontains=query)
        )
        
        if color := request.query_params.get('color'):
            search_q &= Q(color_category=color)
        
        if brand := request.query_params.get('brand'):
            search_q &= Q(brand__icontains=brand)
        
        products = Product.objects.filter(search_q).order_by('-color_confidence', '-created_at')
        
        max_results = min(int(request.query_params.get('limit', 50)), 100)
        products = products[:max_results]
        
        serializer = ProductSerializer(products, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'count': len(serializer.data),
            'total_matches': Product.objects.filter(search_q).count(),
            'search_query': query
        })

    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        """Find product by exact barcode match"""
        barcode = request.query_params.get('barcode', '').strip()
        if not barcode:
            return Response({'found': False, 'message': 'No barcode provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(barcode=barcode)
            return Response({'found': True, 'product': ProductSerializer(product, context={'request': request}).data})
        except Product.DoesNotExist:
            return Response({'found': False, 'message': f'No product found with barcode: {barcode}'})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser, FormParser])
    def add_from_barcode(self, request):
        """Add product from barcode with simple processing"""
        serializer = ProductBarcodeSerializer(data=request.data)
        
        if serializer.is_valid():
            barcode = serializer.validated_data['barcode']
            auto_process = serializer.validated_data.get('auto_process', True)
            
            try:
                product = Product.objects.get(barcode=barcode)
                return Response({
                    'detail': 'Product with this barcode already exists',
                    'product': ProductSerializer(product, context={'request': request}).data
                }, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                product_data = {
                    'name': serializer.validated_data['name'], 'barcode': barcode,
                    'brand': serializer.validated_data.get('brand', ''), 'category': serializer.validated_data.get('category', ''),
                    'weight': serializer.validated_data.get('weight', ''),
                }
                
                image = request.FILES.get('image')
                if image and auto_process:
                    try:
                        color_info = categorize_by_color(image)
                        product_data.update({
                            'color_category': color_info['category'], 'color_confidence': color_info['confidence'],
                            'dominant_colors': color_info.get('colors', [])
                        })
                        visual_features = extract_visual_features_resnet(image, color_category=color_info['category'])
                        product_data['visual_embedding'] = visual_features.tolist()
                        text_embedding = get_color_aware_text_embedding(product_data['name'], color_info['category'])
                        product_data['color_aware_text_embedding'] = text_embedding.tolist()
                        product_data.update({'processing_status': 'completed', 'processed_at': timezone.now()})
                        logger.info(f"Simple processing for {product_data['name']}: {color_info['category']}")
                    except Exception as e:
                        logger.error(f"Image processing error: {str(e)}")
                        product_data.update({'processing_status': 'failed', 'processing_error': str(e)})
                
                product = Product.objects.create(**product_data)
                if image:
                    product.image.save(f"product_{product.id}.jpg", image, save=True)
                
                return Response({
                    'detail': 'Product created successfully',
                    'product': ProductSerializer(product, context={'request': request}).data
                }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser, FormParser])
    def identify(self, request):
        """Simple product identification (Legacy)"""
        serializer = ProductIdentificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        image = serializer.validated_data['image']
        start_time = time.time()
        
        try:
            identified_product = identify_product(image)
            processing_time = time.time() - start_time
            if identified_product:
                return Response({
                    'found': True, 'product': ProductSerializer(identified_product, context={'request': request}).data,
                    'processing_time': processing_time, 'method': 'simple_ai_detection'
                })
            else:
                color_info = categorize_by_color(image)
                return Response({
                    'found': False, 'processing_time': processing_time, 'color_info': color_info,
                    'suggestions': self._get_color_based_suggestions(color_info['category'])
                })
        except Exception as e:
            return Response({'found': False, 'error': str(e), 'processing_time': time.time() - start_time}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def gallery(self, request):
        """Get products with images for gallery display"""
        queryset = Product.objects.filter(
            Q(image__isnull=False) | Q(image_url__isnull=False) | Q(image_front_url__isnull=False)
        ).exclude(image_url='').exclude(image_front_url='')
        
        if color_category := request.query_params.get('color'):
            queryset = queryset.filter(color_category=color_category)
        if brand := request.query_params.get('brand'):
            queryset = queryset.filter(brand__icontains=brand)
        
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start, end = (page - 1) * page_size, page * page_size
        products = queryset.order_by('-created_at')[start:end]
        total_count = queryset.count()
        
        serialized_products = ProductSerializer(products, many=True, context={'request': request})
        
        return Response({
            'products': serialized_products.data,
            'pagination': {
                'page': page, 'page_size': page_size, 'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': end < total_count, 'has_previous': page > 1
            }
        })

    @action(detail=True, methods=['get'])
    def image_info(self, request, pk=None):
        """Get detailed image information for a product"""
        product = self.get_object()
        image_data = {
            'product_id': product.id, 'product_name': product.name,
            'has_local_image': bool(product.image), 'has_url_image': bool(product.image_url),
            'has_front_image': bool(product.image_front_url), 'display_url': product.get_image_url(),
            'color_info': {'category': product.color_category, 'confidence': product.color_confidence, 'display_name': product.get_color_display()}
        }
        if product.image:
            try:
                image_data['local_image'] = {'url': request.build_absolute_uri(product.image.url), 'size': product.image.size}
            except: pass
        return Response(image_data)

    @action(detail=False, methods=['get'])
    def color_stats(self, request):
        """Get color category statistics"""
        try:
            color_stats = Product.objects.values('color_category').annotate(count=Count('id'), avg_confidence=Avg('color_confidence')).order_by('-count')
            total_products = Product.objects.count()
            results = [{
                'color_category': stat['color_category'], 'display_name': dict(Product.COLOR_CHOICES).get(stat['color_category'], stat['color_category']),
                'count': stat['count'], 'percentage': (stat['count'] / total_products * 100) if total_products > 0 else 0,
                'avg_confidence': stat['avg_confidence'] or 0.0
            } for stat in color_stats]
            return Response({
                'color_distribution': results, 'total_products': total_products,
                'processed_products': Product.objects.exclude(color_category='unknown').count()
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Get similar products"""
        product = self.get_object()
        if not product.visual_embedding:
            return Response({'error': 'Product has no visual features'}, status=status.HTTP_400_BAD_REQUEST)
        
        max_results = int(request.query_params.get('max_results', 5))
        try:
            vector_index = get_vector_index()
            candidates = vector_index.search(np.array(product.visual_embedding), search_categories=[product.color_category], k=max_results + 1)
            
            recommendations = []
            for candidate in candidates:
                if candidate['product_id'] == product.id: continue
                try:
                    similar_product = Product.objects.get(id=candidate['product_id'])
                    similarity = 1.0 - min(candidate['distance'] / 100.0, 1.0)
                    product_data = ProductSerializer(similar_product, context={'request': request}).data
                    product_data.update({'similarity_score': similarity, 'color_match': candidate.get('is_exact_color_match', False)})
                    recommendations.append(product_data)
                except Product.DoesNotExist: continue
            
            return Response({
                'source_product': ProductSerializer(product, context={'request': request}).data,
                'similar_products': recommendations[:max_results]
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_color_based_suggestions(self, color_category):
        if color_category == 'unknown': return []
        similar_products = Product.objects.filter(color_category=color_category).order_by('-color_confidence')[:5]
        return [{'id': p.id, 'name': p.name, 'brand': p.brand, 'confidence': p.color_confidence, 'image_url': p.get_image_url()} for p in similar_products]

    def _extract_brand_from_text(self, text):
        if not text: return ''
        words = text.strip().split()
        if not words: return ''
        known_brands = ['ÜLKER', 'ETİ', 'PINAR', 'SÜTAŞ', 'İÇİM', 'HARNAS', 'NESTLE', 'DANONE', 'COCA', 'COLA', 'PEPSI', 'FANTA', 'SPRITE', 'LAY\'S', 'DORITOS', 'TORKU', 'SELSA', 'BANVIT', 'BEYPAZARI', 'KALE', 'DIMES', 'CAPPY', 'EFES', 'BOĞAZIÇI', 'ALGIDA', 'MAGNUM']
        for word in words[:3]:
            word_upper = word.upper().strip('.,!?()[]{}""''')
            if word_upper in known_brands: return word_upper
            for brand in known_brands:
                if word_upper in brand or brand in word_upper: return brand
        first_word = words[0].strip('.,!?()[]{}""''')
        if len(first_word) > 2 and first_word.isupper(): return first_word
        return ''

    def _clean_product_name(self, text):
        if not text: return ''
        import re
        cleaned = re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\t', ' ')).strip()
        cleaned = re.sub(r'[|\\/_]+', ' ', cleaned)
        cleaned = re.sub(r'[^\w\s\-.,()%]', '', cleaned)
        words = cleaned.split()
        if words:
            cleaned_words = [words[0]] if words[0].isupper() and len(words[0]) > 2 else [words[0].capitalize()]
            for word in words[1:]:
                cleaned_words.append(word if word.isupper() and len(word) > 2 else word.lower())
            cleaned = ' '.join(cleaned_words)
        return cleaned[:97] + '...' if len(cleaned) > 100 else cleaned

    def _extract_weight_from_text(self, text):
        if not text: return ''
        import re
        patterns = [r'(\d+(?:[.,]\d+)?)\s*(kg|kilo|kilogram)', r'(\d+(?:[.,]\d+)?)\s*(g|gr|gram)', r'(\d+(?:[.,]\d+)?)\s*(ml|mililitre)', r'(\d+(?:[.,]\d+)?)\s*(l|lt|litre|liter)', r'(\d+(?:[.,]\d+)?)\s*(%)', r'(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(g|ml|kg|l)']
        for pattern in patterns:
            if matches := re.findall(pattern, text, re.IGNORECASE):
                if len(matches[0]) == 3:
                    count, amount, unit = matches[0]
                    return f"{count}x{amount}{unit.lower()}"
                else:
                    amount, unit = matches[0]
                    return f"{amount.replace(',', '.')}{unit.lower()}"
        return ''

    @action(detail=False, methods=['post'], url_path='create-from-image', permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser, FormParser])
    def create_from_image(self, request):
            """
            [CORRECTED] Creates a product from an uploaded image and correctly
            launches the background task for AI processing.
            """
            serializer = ProductCreationSerializer(data=request.data, context={'request': request})

            if not serializer.is_valid():
                logger.error(f"Product creation validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # The serializer's .create() method is now responsible for the entire process.
            # It handles creating the product, saving the image, and launching the task.
            product = serializer.save()
            
            logger.info(f"Product {product.id} created and queued for processing.")
            
            return Response({
                'success': True,
                'message': 'Product created and queued for processing.',
                'product': ProductSerializer(product).data
            }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'], url_path='find-similar-by-image', permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser, FormParser])
    def find_similar_by_image(self, request):
        """
        DEPRECATED: This synchronous method is too memory intensive and causes server crashes.
        It has been replaced by the asynchronous `start-visual-search` and `get-visual-search-result` endpoints.
        This endpoint is left here to return an informative error.
        """
        logger.warning("Deprecated synchronous find_similar_by_image endpoint was called.")
        return Response(
            {'error': 'This endpoint is deprecated. Please use the asynchronous search flow.', 'success': False},
            status=status.HTTP_410_GONE  # 410 Gone is the appropriate status code
        )
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a product instance, using Redis cache if available.
        """
        product_id = kwargs.get('pk')
        
        # Try to get from cache first
        cached_product_data = get_cached_product(product_id)
        if cached_product_data:
            logger.info(f"Cache HIT for product {product_id}")
            return Response(cached_product_data)
            
        # If not in cache, get from DB
        logger.info(f"Cache MISS for product {product_id}")
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Cache the result for next time
        cache_product(product_id, serializer.data)
        
        return Response(serializer.data)
    
    
    @action(detail=False, methods=['post'], url_path='start-visual-search', permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser, FormParser])
    def start_visual_search(self, request):
        if 'image' not in request.FILES:
            return Response({'error': 'Image file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        job = VisualSearchJob.objects.create(user=request.user, temp_image=image_file)
        task = perform_visual_search.delay(str(job.id))
        job.task_id = task.id
        job.save()
        
        return Response({
            'success': True,
            'job_id': job.id,
            'message': 'Visual search job has been started.'
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='visual-search-result', permission_classes=[IsAuthenticated])
    def get_visual_search_result(self, request):
        job_id = request.query_params.get('job_id')
        if not job_id:
            return Response({'status': 'FAILURE', 'error': 'job_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = VisualSearchJob.objects.get(id=job_id)
            if job.user != request.user and not request.user.is_superuser:
                return Response({'status': 'FAILURE', 'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
            if job.status == 'SUCCESS':
                try:
                    results_data = json.loads(job.results) if isinstance(job.results, str) else job.results
                except (json.JSONDecodeError, TypeError):
                    results_data = {'candidates': [], 'image_analysis': {}, 'error': 'Failed to parse results'}
                return Response({'status': job.status, 'results': results_data})

            elif job.status == 'FAILURE':
                return Response({'status': job.status, 'error': job.error_message or 'An unknown processing error occurred.'})

            else:
                return Response({'status': job.status})
        except VisualSearchJob.DoesNotExist:
            return Response({'status': 'FAILURE', 'error': 'Job not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching visual search result for job {job_id}: {e}", exc_info=True)
            return Response({'status': 'FAILURE', 'error': 'A server error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def prices(self, request, pk=None): # The 'pk=None' is crucial
        """
        Returns a list of all prices for a given product.
        """
        logger.info(f"Fetching prices for product with pk={pk}")
        try:
            # self.get_object() correctly uses the 'pk' from the URL to find the product
            product = self.get_object() 
            
            # Efficiently fetch prices with related store data to avoid N+1 queries
            prices_queryset = Price.objects.filter(product=product).select_related('store').order_by('-created_at')
            
            logger.info(f"Found {prices_queryset.count()} prices for product '{product.name}'")

            # Use the existing PriceSerializer to format the data
            serializer = PriceSerializer(prices_queryset, many=True, context={'request': request})
            return Response(serializer.data)

        except Product.DoesNotExist:
            logger.warning(f"Product with pk={pk} not found for price lookup.")
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the full error to the console for easy debugging
            logger.error(f"Error fetching prices for product {pk}: {e}", exc_info=True) 
            return Response({'error': 'An internal server error occurred while fetching prices.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PriceViewSet(viewsets.ModelViewSet):
    queryset = Price.objects.all()
    serializer_class = PriceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        ⭐ --- START OF FIX 2 --- ⭐
        This is the new, robust queryset for the History screen.
        It efficiently fetches the price, its related product, store, and user
        all in a single database query, solving the N+1 and timeout problems.
        """
        user = self.request.user
        if not user.is_authenticated:
            return Price.objects.none() # Return empty queryset if not logged in

        # The key is .select_related('product', 'store', 'user')
        # This pre-fetches all related data efficiently.
        queryset = Price.objects.select_related('product', 'store', 'user').filter(user=user)
        
        return queryset.order_by('-created_at')
        # ⭐ --- END OF FIX 2 --- ⭐
    
    def get_serializer_class(self):
        """
        This method tells Django Rest Framework which serializer to use
        based on the action (e.g., creating vs. reading).
        """
        if self.action == 'create':
            # When the frontend sends a POST request, use the PriceCreationSerializer.
            return PriceCreationSerializer
        # For all other actions (list, retrieve), use the default PriceSerializer.
        return PriceSerializer
    def perform_create(self, serializer):
        """This correctly sets the user when a new price is created."""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def add_price(self, request):
        """Add price with color context"""
        product_id = request.data.get('product')
        store_id = request.data.get('store')
        price = request.data.get('price')
        
        if not all([product_id, store_id, price]):
            return Response({'error': 'Product, store, and price are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(pk=product_id)
            store = Store.objects.get(pk=store_id)
            
            price_obj = Price.objects.create(
                product=product,
                store=store,
                price=price,
                user=request.user
            )
            
            response_data = PriceSerializer(price_obj).data
            response_data['product_color_info'] = {
                'category': product.color_category,
                'display_name': product.get_color_display(),
                'confidence': product.color_confidence
            }
            
            return Response({
                'detail': 'Price added successfully',
                'price': response_data
            }, status=status.HTTP_201_CREATED)
            
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]  # Allow creation without auth
    
    def create(self, request, *args, **kwargs):
        """Enhanced store creation with better error handling"""
        try:
            # Log the incoming data
            print(f"Store creation request: {request.data}")
            
            # Validate required fields
            name = request.data.get('name', '').strip()
            if not name:
                return Response({
                    'error': 'Store name is required',
                    'detail': 'Please provide a valid store name'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check for duplicate stores in same location
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            
            if latitude and longitude:
                # Check if store exists within 100m radius
                existing_store = Store.objects.filter(
                    name__iexact=name,
                    latitude__range=[float(latitude) - 0.001, float(latitude) + 0.001],
                    longitude__range=[float(longitude) - 0.001, float(longitude) + 0.001]
                ).first()
                
                if existing_store:
                    return Response({
                        'error': 'Store already exists at this location',
                        'existing_store': StoreSerializer(existing_store).data
                    }, status=status.HTTP_409_CONFLICT)
            
            # Create the store
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                store = serializer.save()
                
                # Log successful creation
                print(f"Store created successfully: {store.name} (ID: {store.id})")
                
                return Response({
                    'detail': 'Store created successfully',
                    'store': StoreSerializer(store).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'Invalid data provided',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f"Store creation error: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request, *args, **kwargs):
        """
        ⭐ OPTIMIZED LIST METHOD ⭐
        This version uses database-level annotations for both product counts
        and distance calculation, reducing N+1 queries to a single efficient query.
        """
        # Annotate every store with its distinct product count in one go.
        queryset = Store.objects.annotate(
            product_count=Count('price__product', distinct=True)
        )

        user_lat = request.query_params.get('lat')
        user_lng = request.query_params.get('lng')
        
        # If location is provided, annotate with Haversine distance and order by it.
        if user_lat and user_lng:
            try:
                user_lat_rad = Radians(float(user_lat))
                user_lng_rad = Radians(float(user_lng))

                # Haversine formula implemented with Django ORM functions
                dlat = Radians(F('latitude')) - user_lat_rad
                dlon = Radians(F('longitude')) - user_lng_rad
                
                a = (
                    Sin(dlat / 2) * Sin(dlat / 2) +
                    Cos(user_lat_rad) * Cos(Radians(F('latitude'))) *
                    Sin(dlon / 2) * Sin(dlon / 2)
                )
                c = 2 * ASin(Sqrt(a))
                r = 6371  # Earth radius in kilometers

                # Annotate each store with the calculated distance
                queryset = queryset.annotate(
                    distance=ExpressionWrapper(r * c, output_field=FloatField())
                ).order_by('distance')

            except (ValueError, TypeError):
                # If lat/lng are invalid, ignore them and continue with default ordering.
                queryset = queryset.order_by('name')
        else:
            queryset = queryset.order_by('name')

        # Now, when we serialize, the `product_count` and `distance` fields are already on each object.
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Earth's radius in kilometers
        
        return c * r

# Simple API endpoints for testing
@api_view(['GET'])
def test_visual_index(request):
    """Test the vector index"""
    try:
        index = get_vector_index()
        
        stats = {}
        total_products = 0
        
        for color, color_index in index.color_indices.items():
            count = color_index['index'].ntotal
            stats[color] = {
                'count': count,
                'display_name': dict(Product.COLOR_CHOICES).get(color, color)
            }
            total_products += count
        
        return Response({
            'status': 'success',
            'total_indexed_products': total_products,
            'color_distribution': stats,
            'index_type': 'SimpleVectorIndex'
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def quick_color_test(request):
    """Quick color analysis test endpoint"""
    if 'image' not in request.FILES:
        return Response({
            'error': 'Image required'
        }, status=400)
    
    try:
        image = request.FILES['image']
        color_info = categorize_by_color(image)
        
        similar_products = Product.objects.filter(
            color_category=color_info['category']
        ).order_by('-color_confidence')[:5]
        
        return Response({
            'color_analysis': color_info,
            'similar_products': [
                {
                    'id': p.id,
                    'name': p.name,
                    'brand': p.brand,
                    'confidence': p.color_confidence,
                    'image_url': p.get_image_url()
                }
                for p in similar_products
            ]
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=500)

@api_view(['GET'])
def processing_stats(request):
    """Get processing statistics"""
    try:
        total_products = Product.objects.count()
        
        stats = {
            'total_products': total_products,
            'color_analyzed': Product.objects.exclude(color_category='unknown').count(),
            'with_visual_features': Product.objects.filter(visual_embedding__isnull=False).count(),
            'with_images': Product.objects.filter(
                Q(image__isnull=False) | 
                Q(image_url__isnull=False) | 
                Q(image_front_url__isnull=False)
            ).exclude(image_url='').exclude(image_front_url='').count(),
            'fully_processed': Product.objects.filter(
                processing_status='completed'
            ).count(),
            'processing_failed': Product.objects.filter(
                processing_status='failed'
            ).count(),
            'pending_processing': Product.objects.filter(
                processing_status='pending'
            ).count(),
        }
        
        confidence_ranges = [
            (0.0, 0.3, 'Low'),
            (0.3, 0.6, 'Medium'),
            (0.6, 0.8, 'High'),
            (0.8, 1.0, 'Very High')
        ]
        
        confidence_stats = {}
        for min_conf, max_conf, label in confidence_ranges:
            count = Product.objects.filter(
                color_confidence__gte=min_conf,
                color_confidence__lt=max_conf
            ).count()
            confidence_stats[label] = count
        
        stats['confidence_distribution'] = confidence_stats
        
        return Response(stats)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=500)

@api_view(['POST'])
def rebuild_index(request):
    """Rebuild the vector index"""
    try:
        start_time = time.time()
        from .util import build_vector_index
        build_vector_index()
        processing_time = time.time() - start_time
        
        return Response({
            'message': 'Vector index rebuilt successfully',
            'processing_time': processing_time
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=500)