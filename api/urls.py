# api/urls.py - Fixed version to ensure ViewSet actions work

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, PriceViewSet, StoreViewSet,
    test_visual_index, quick_color_test, processing_stats, rebuild_index
)
from .views_user import (
    RegisterView, CustomAuthToken, UserDetailView, 
    logout_view, change_password
)

# Create router and register ViewSets
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'prices', PriceViewSet, basename='price')
router.register(r'stores', StoreViewSet, basename='store')

# URL patterns
urlpatterns = [
    # Include router URLs first (this handles ViewSet actions)
    path('', include(router.urls)),
    
    # User authentication URLs 
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomAuthToken.as_view(), name='login'),
    path('auth/me/', UserDetailView.as_view(), name='user-detail'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/change-password/', change_password, name='change-password'),
        

    # Utility endpoints (function-based views)
    path('test-visual-index/', test_visual_index, name='test-visual-index'),
    path('quick-color-test/', quick_color_test, name='quick-color-test'),
    path('processing-stats/', processing_stats, name='processing-stats'),
    path('rebuild-index/', rebuild_index, name='rebuild-index'),
]

# Debug: Print registered routes (remove in production)
import sys
if 'runserver' in sys.argv:
    print("🔗 Registered ViewSet routes:")
    for prefix, viewset, basename in router.registry:
        print(f"  {prefix}/ -> {viewset.__name__} (basename: {basename})")
        
        # Check for custom actions
        if hasattr(viewset, 'get_extra_actions'):
            try:
                actions = viewset.get_extra_actions()
                if actions:
                    print(f"    Custom actions: {[action.__name__ for action in actions]}")
            except:
                pass