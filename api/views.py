# api/views.py - Enhanced with Color-Aware Processing
from django.shortcuts import render, get_object_or_404
from django.db import models
from django.db.models.expressions import RawSQL
from django.db.models import Min, Count, F, Q, Avg
from django.utils import timezone
from datetime import timedelta
import time
import numpy as np


from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Product, Store, Price, ProcessingJob, ColorAnalysisStats
from .serializers import (
    ProductSerializer, PriceSerializer, StoreSerializer,
    ProductCreationSerializer, ProductBarcodeSerializer,
    ProductIdentificationSerializer, ProductSearchSerializer,
    ColorAnalysisSerializer, ProductSimilaritySerializer,
    ProcessingJobSerializer, ProductColorStatsSerializer,
    BulkProductProcessingSerializer, ProductRecommendationSerializer
)
from .util import *


# Enhanced detection integration
try:
    from .util_enhanced import (
        enhanced_product_preprocessing,
        extract_visual_features_enhanced,
        process_product_image_enhanced,
        EnhancedProductDetector
    )
    ENHANCED_DETECTION_AVAILABLE = True
except ImportError:
    ENHANCED_DETECTION_AVAILABLE = False

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Enhanced queryset with color filtering"""
        queryset = Product.objects.all()
        
        # Color filtering
        color_category = self.request.query_params.get('color')
        if color_category and color_category in dict(Product.COLOR_CHOICES):
            queryset = queryset.filter(color_category=color_category)
        
        # Processing status filtering
        processing_status = self.request.query_params.get('processing_status')
        if processing_status:
            queryset = queryset.filter(processing_status=processing_status)
        
        # Confidence filtering
        min_confidence = self.request.query_params.get('min_confidence')
        if min_confidence:
            try:
                min_conf = float(min_confidence)
                queryset = queryset.filter(color_confidence__gte=min_conf)
            except ValueError:
                pass
        
        # Has features filtering
        has_features = self.request.query_params.get('has_features')
        if has_features:
            if has_features.lower() == 'true':
                queryset = queryset.filter(visual_embedding__isnull=False)
            elif has_features.lower() == 'false':
                queryset = queryset.filter(visual_embedding__isnull=True)
        
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @parser_classes([MultiPartParser, FormParser])
    def add_from_barcode(self, request):
        """Enhanced barcode product addition with intelligent product detection"""
        serializer = ProductBarcodeSerializer(data=request.data)
        
        if serializer.is_valid():
            barcode = serializer.validated_data['barcode']
            auto_process = serializer.validated_data.get('auto_process', True)
            
            # Check if product already exists
            try:
                product = Product.objects.get(barcode=barcode)
                return Response({
                    'detail': 'Product with this barcode already exists',
                    'product': ProductSerializer(product).data
                }, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                # Create new product
                product_data = {
                    'name': serializer.validated_data['name'],
                    'barcode': barcode,
                    'brand': serializer.validated_data.get('brand', ''),
                    'category': serializer.validated_data.get('category', ''),
                    'weight': serializer.validated_data.get('weight', ''),
                }
                
                # Process image if provided
                image = request.FILES.get('image')
                if image and auto_process:
                    try:
                        if ENHANCED_DETECTION_AVAILABLE:
                            # Use enhanced processing pipeline
                            processing_results, success = process_product_image_enhanced(
                                image,
                                product_id=barcode,
                                save_processed=True,
                                processed_dir='processed_products'
                            )
                            
                            if success:
                                # Extract results from enhanced processing
                                preprocessing_info = processing_results['preprocessing_info']
                                color_info = processing_results['color_info']
                                visual_features = processing_results['visual_features']
                                
                                # Update product data with enhanced results
                                product_data.update({
                                    'color_category': color_info['category'],
                                    'color_confidence': color_info['confidence'],
                                    'dominant_colors': color_info.get('colors', [])
                                })
                                
                                if visual_features:
                                    product_data['visual_embedding'] = visual_features
                                
                                # Generate color-aware text embedding
                                text_embedding = get_color_aware_text_embedding(
                                    product_data['name'], 
                                    color_info['category']
                                )
                                product_data['color_aware_text_embedding'] = text_embedding.tolist()
                                
                                product_data.update({
                                    'processing_status': 'completed',
                                    'processed_at': timezone.now()
                                })
                                
                                # Log enhanced processing details
                                detection_result = preprocessing_info.get('detection_result')
                                logger.info(f"Enhanced processing for {product_data['name']}: "
                                        f"steps={preprocessing_info['steps_applied']}, "
                                        f"detection={detection_result.get('detection_method') if detection_result else 'none'}")
                            else:
                                logger.warning(f"Enhanced processing failed: {processing_results.get('error')}")
                                product_data.update({
                                    'processing_status': 'failed',
                                    'processing_error': processing_results.get('error', 'Enhanced processing failed')
                                })
                        else:
                            # Fallback to standard processing
                            logger.info("Using standard processing (enhanced not available)")
                            
                            # Standard color analysis
                            color_info = categorize_by_color(image)
                            product_data.update({
                                'color_category': color_info['category'],
                                'color_confidence': color_info['confidence'],
                                'dominant_colors': color_info.get('colors', [])
                            })
                            
                            # Standard visual features
                            visual_features = extract_visual_features_resnet(
                                image, remove_bg=True, color_category=color_info['category']
                            )
                            product_data['visual_embedding'] = visual_features.tolist()
                            
                            # Standard text embedding
                            text_embedding = get_color_aware_text_embedding(
                                product_data['name'], color_info['category']
                            )
                            product_data['color_aware_text_embedding'] = text_embedding.tolist()
                            
                            product_data.update({
                                'processing_status': 'completed',
                                'processed_at': timezone.now()
                            })
                            
                    except Exception as e:
                        logger.error(f"Image processing error: {str(e)}")
                        product_data.update({
                            'processing_status': 'failed',
                            'processing_error': str(e)
                        })
                
                # Create product
                product = Product.objects.create(**product_data)
                
                response_data = {
                    'detail': 'Product created successfully',
                    'product': ProductSerializer(product).data,
                    'enhanced_processing': ENHANCED_DETECTION_AVAILABLE and auto_process and image
                }
                
                # Add processing info if enhanced was used
                if ENHANCED_DETECTION_AVAILABLE and 'processing_results' in locals():
                    response_data['processing_info'] = processing_results.get('preprocessing_info', {})
                
                return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @parser_classes([MultiPartParser, FormParser])
    def identify(self, request):
        """Enhanced product identification with intelligent detection"""
        serializer = ProductIdentificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        image = serializer.validated_data['image']
        color_hint = serializer.validated_data.get('color_hint')
        
        start_time = time.time()
        
        try:
            if ENHANCED_DETECTION_AVAILABLE:
                # Use enhanced identification
                identified_product = identify_product_enhanced(image)
                processing_time = time.time() - start_time
                
                if identified_product:
                    return Response({
                        'found': True,
                        'product': ProductSerializer(identified_product).data,
                        'processing_time': processing_time,
                        'method': 'enhanced_ai_detection'
                    })
                else:
                    # Enhanced analysis for failed identification
                    try:
                        processed_image, preprocessing_info = enhanced_product_preprocessing(image, method='auto')
                        color_info = categorize_by_color(processed_image)
                        
                        # Try to detect product even if not in database
                        detector = EnhancedProductDetector()
                        detection_result = detector.detect_product(processed_image)
                        
                        response_data = {
                            'found': False,
                            'processing_time': processing_time,
                            'color_info': color_info,
                            'suggestions': self._get_color_based_suggestions(color_info['category']),
                            'preprocessing_applied': preprocessing_info['steps_applied']
                        }
                        
                        if detection_result:
                            response_data['detection_info'] = {
                                'method': detection_result.get('detection_method'),
                                'confidence': detection_result.get('confidence'),
                                'bbox': detection_result.get('bbox'),
                                'message': 'Product detected but not in database - consider adding it'
                            }
                        
                        return Response(response_data)
                        
                    except Exception as e:
                        logger.error(f"Enhanced analysis failed: {str(e)}")
            
            # Fallback to standard identification
            identified_product = identify_product_enhanced(image)
            processing_time = time.time() - start_time
            
            if identified_product:
                return Response({
                    'found': True,
                    'product': ProductSerializer(identified_product).data,
                    'processing_time': processing_time,
                    'method': 'standard_ai_detection'
                })
            else:
                # Try barcode as final fallback
                barcode = scan_barcode(image)
                if barcode:
                    try:
                        product = Product.objects.get(barcode=barcode)
                        return Response({
                            'found': True,
                            'product': ProductSerializer(product).data,
                            'processing_time': processing_time,
                            'method': 'barcode',
                            'barcode': barcode
                        })
                    except Product.DoesNotExist:
                        pass
                
                # Provide basic color information for failed identification
                color_info = categorize_by_color(image)
                
                return Response({
                    'found': False,
                    'processing_time': processing_time,
                    'color_info': color_info,
                    'suggestions': self._get_color_based_suggestions(color_info['category'])
                })
                    
        except Exception as e:
            return Response({
                'found': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    # Add this new endpoint for testing enhanced detection:

    @action(detail=False, methods=['post'])
    @parser_classes([MultiPartParser, FormParser])
    def test_enhanced_detection(self, request):
        """Test enhanced detection capabilities on uploaded image"""
        if 'image' not in request.FILES:
            return Response({'error': 'Image required'}, status=400)
        
        if not ENHANCED_DETECTION_AVAILABLE:
            return Response({'error': 'Enhanced detection not available'}, status=500)
        
        try:
            image = request.FILES['image']
            start_time = time.time()
            
            # Test enhanced preprocessing
            processed_image, preprocessing_info = enhanced_product_preprocessing(image, method='full')
            
            # Test detection
            detector = EnhancedProductDetector()
            detection_result = detector.detect_product(image)
            
            # Test color analysis
            color_info = categorize_by_color(processed_image)
            
            processing_time = time.time() - start_time
            
            response_data = {
                'preprocessing_info': preprocessing_info,
                'detection_result': detection_result,
                'color_analysis': color_info,
                'processing_time': processing_time,
                'success': True
            }
            
            # If product detected, show crop comparison
            if detection_result and 'bbox' in detection_result:
                x1, y1, x2, y2 = detection_result['bbox']
                crop_info = {
                    'original_size': preprocessing_info['original_size'],
                    'detected_area': {
                        'coordinates': [x1, y1, x2, y2],
                        'width': x2 - x1,
                        'height': y2 - y1
                    },
                    'crop_coverage': ((x2 - x1) * (y2 - y1)) / (preprocessing_info['original_size'][0] * preprocessing_info['original_size'][1])
                }
                response_data['crop_analysis'] = crop_info
            
            return Response(response_data)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'success': False
            }, status=500)
    
    @action(detail=False, methods=['get'])
    def color_stats(self, request):
        """Get color category statistics"""
        try:
            # Get color distribution
            color_stats = Product.objects.values('color_category').annotate(
                count=Count('id'),
                avg_confidence=Avg('color_confidence')
            ).order_by('-count')
            
            total_products = Product.objects.count()
            
            results = []
            for stat in color_stats:
                color = stat['color_category']
                count = stat['count']
                results.append({
                    'color_category': color,
                    'display_name': dict(Product.COLOR_CHOICES).get(color, color),
                    'count': count,
                    'percentage': (count / total_products * 100) if total_products > 0 else 0,
                    'avg_confidence': stat['avg_confidence'] or 0.0
                })
            
            return Response({
                'color_distribution': results,
                'total_products': total_products,
                'processed_products': Product.objects.exclude(color_category='unknown').count()
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_process(self, request):
        """Bulk process products with color analysis and features"""
        serializer = BulkProductProcessingSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product_ids = serializer.validated_data['product_ids']
        job_types = serializer.validated_data['job_types']
        priority = serializer.validated_data['priority']
        force_reprocess = serializer.validated_data['force_reprocess']
        
        # Validate products exist
        products = Product.objects.filter(id__in=product_ids)
        if products.count() != len(product_ids):
            return Response({
                'error': 'Some product IDs not found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create processing jobs
        jobs_created = []
        for product in products:
            for job_type in job_types:
                # Check if already processed (unless force reprocess)
                if not force_reprocess:
                    if job_type == 'color_analysis' and product.has_color_analysis:
                        continue
                    if job_type == 'visual_features' and product.has_visual_features:
                        continue
                
                job = ProcessingJob.objects.create(
                    product=product,
                    job_type=job_type,
                    priority=priority,
                    status='queued'
                )
                jobs_created.append(job.id)
        
        return Response({
            'message': f'{len(jobs_created)} processing jobs created',
            'job_ids': jobs_created,
            'products_affected': products.count()
        })
    
    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """Get product recommendations based on color and visual similarity"""
        product = self.get_object()
        
        serializer = ProductRecommendationSerializer(data={
            'source_product_id': product.id,
            **request.query_params.dict()
        })
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        max_recommendations = serializer.validated_data['max_recommendations']
        color_weight = serializer.validated_data['color_weight']
        visual_weight = serializer.validated_data['visual_weight']
        text_weight = serializer.validated_data['text_weight']
        
        try:
            recommendations = self._get_product_recommendations(
                product, max_recommendations, color_weight, visual_weight, text_weight
            )
            
            return Response({
                'source_product': ProductSerializer(product).data,
                'recommendations': recommendations,
                'weights': {
                    'color': color_weight,
                    'visual': visual_weight,
                    'text': text_weight
                }
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_color_based_suggestions(self, color_category):
        """Get product suggestions based on color category"""
        if color_category == 'unknown':
            return []
        
        similar_products = Product.objects.filter(
            color_category=color_category
        ).order_by('-color_confidence')[:5]
        
        return [
            {
                'id': p.id,
                'name': p.name,
                'brand': p.brand,
                'confidence': p.color_confidence
            }
            for p in similar_products
        ]
    
    def _get_product_recommendations(self, source_product, max_results, color_weight, visual_weight, text_weight):
        """Generate product recommendations using multiple similarity metrics"""
        if not source_product.has_visual_features:
            return []
        
        try:
            # Get visual similarities
            vector_index = get_enhanced_vector_index()
            visual_candidates = vector_index.search(
                source_product.visual_embedding,
                color_category=source_product.color_category,
                k=max_results * 3,  # Get more candidates for better selection
                search_similar_colors=True
            )
            
            recommendations = []
            for candidate in visual_candidates:
                try:
                    product = Product.objects.get(id=candidate['product_id'])
                    if product.id == source_product.id:
                        continue
                    
                    # Calculate visual similarity
                    visual_sim = 1.0 - min(candidate['distance'] / 100.0, 1.0)
                    
                    # Calculate color similarity
                    color_sim = 1.0 if product.color_category == source_product.color_category else 0.3
                    if candidate['is_exact_color_match']:
                        color_sim = 1.0
                    
                    # Calculate text similarity (if available)
                    text_sim = 0.5  # Default
                    if (source_product.color_aware_text_embedding and 
                        product.color_aware_text_embedding):
                        # Simplified text similarity calculation
                        text_sim = 0.8  # Placeholder
                    
                    # Combined score
                    combined_score = (
                        color_weight * color_sim +
                        visual_weight * visual_sim +
                        text_weight * text_sim
                    )
                    
                    product_data = ProductSerializer(product).data
                    product_data.update({
                        'similarity_score': combined_score,
                        'visual_similarity': visual_sim,
                        'color_similarity': color_sim,
                        'text_similarity': text_sim
                    })
                    
                    recommendations.append(product_data)
                    
                except Product.DoesNotExist:
                    continue
            
            # Sort by combined score and return top results
            recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            return recommendations[:max_results]
            
        except Exception as e:
            print(f"Recommendation error: {e}")
            return []

class PriceViewSet(viewsets.ModelViewSet):
    queryset = Price.objects.all()
    serializer_class = PriceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Enhanced queryset with color-based filtering"""
        queryset = Price.objects.select_related('product', 'store', 'user').all()
        
        # Color filtering
        color_category = self.request.query_params.get('color')
        if color_category:
            queryset = queryset.filter(product__color_category=color_category)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Automatically set the user when creating a price entry"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def add_price(self, request):
        """Enhanced price addition with color context"""
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
            
            # Include color information in response
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

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @action(detail=True, methods=['get'])
    def color_distribution(self, request, pk=None):
        """Get color distribution of products in this store"""
        store = self.get_object()
        
        try:
            color_stats = Price.objects.filter(store=store).values(
                'product__color_category'
            ).annotate(
                count=Count('product', distinct=True)
            ).order_by('-count')
            
            total_products = Price.objects.filter(store=store).values('product').distinct().count()
            
            results = []
            for stat in color_stats:
                color = stat['product__color_category']
                count = stat['count']
                results.append({
                    'color_category': color,
                    'display_name': dict(Product.COLOR_CHOICES).get(color, color),
                    'count': count,
                    'percentage': (count / total_products * 100) if total_products > 0 else 0
                })
            
            return Response({
                'store': StoreSerializer(store).data,
                'color_distribution': results,
                'total_unique_products': total_products
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProcessingJobViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for monitoring processing jobs"""
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ProcessingJob.objects.select_related('product').all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by job type
        job_type = self.request.query_params.get('job_type')
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def retry(self, request, pk=None):
        """Retry a failed processing job"""
        job = self.get_object()
        
        if not job.can_retry():
            return Response({
                'error': 'Job cannot be retried'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset job status
        job.status = 'queued'
        job.retry_count += 1
        job.error_message = ''
        job.save()
        
        return Response({
            'message': 'Job queued for retry',
            'job': ProcessingJobSerializer(job).data
        })

# API endpoints for testing and debugging
@api_view(['GET'])
def test_enhanced_index(request):
    """Test the enhanced vector index"""
    try:
        index = get_enhanced_vector_index()
        
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
            'index_type': 'ColorAwareProductVectorIndex'
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
        
        # Find similar colored products
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
                    'confidence': p.color_confidence
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
        
        # Processing job statistics
        job_stats = ProcessingJob.objects.values('status').annotate(
            count=Count('id')
        )
        stats['job_statistics'] = {
            item['status']: item['count'] for item in job_stats
        }
        
        # Color confidence distribution
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
    """Rebuild the enhanced vector index"""
    try:
        start_time = time.time()
        build_enhanced_vector_index()
        processing_time = time.time() - start_time
        
        return Response({
            'message': 'Enhanced vector index rebuilt successfully',
            'processing_time': processing_time
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=500)

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula (in km)
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth radius (km)
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance


@api_view(['GET'])
def test_visual_index(request):
    """Test the visual index functionality"""
    try:
        index = get_vector_index()
        return Response({
            'status': 'success',
            'message': 'Visual index is working',
            'total_products': getattr(index, 'index', {}).get('ntotal', 0) if hasattr(index, 'index') else 0
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)