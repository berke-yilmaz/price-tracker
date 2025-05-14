# api/urls.py - Updated Authentication URLs
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, PriceViewSet, StoreViewSet, test_visual_index
from .views_user import RegisterView, CustomAuthToken, UserDetailView, logout_view, change_password

# Router for ViewSets
router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'prices', PriceViewSet)
router.register(r'stores', StoreViewSet)

# URL patterns
urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),
    
    # User authentication URLs 
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomAuthToken.as_view(), name='login'),
    path('auth/me/', UserDetailView.as_view(), name='user-detail'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/change-password/', change_password, name='change-password'),
    
    # Test endpoint
    path('test-visual-index/', test_visual_index, name='test-visual-index'),
]