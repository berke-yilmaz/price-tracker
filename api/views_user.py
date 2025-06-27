# api/views_user.py - FIXED VERSION with proper error handling
from datetime import timezone
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate
import logging

from PriceTracker import settings


from .serializers import UserSerializer, UserRegistrationSerializer, ChangePasswordSerializer

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    """
    Enhanced API endpoint for new user registration with proper error handling
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Registration attempt for: {request.data.get('username', 'unknown')}")
            
            serializer = self.get_serializer(data=request.data)
            
            # Validate the data
            if not serializer.is_valid():
                logger.warning(f"Registration validation failed: {serializer.errors}")
                return Response({
                    'success': False,
                    'error': serializer.errors,
                    **serializer.errors  # Flatten errors for easier client handling
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the user
            user = serializer.save()
            logger.info(f"User created successfully: {user.username}")
            
            # Create token for immediate login
            token, created = Token.objects.get_or_create(user=user)
            
            # Return success response with token and user data
            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Kayıt işlemi sırasında bir hata oluştu',
                'detail': str(e) if settings.DEBUG else 'Sunucu hatası'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomAuthToken(ObtainAuthToken):
    """
    Enhanced token-based login endpoint with proper error handling
    """
    def post(self, request, *args, **kwargs):
        try:
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '')
            
            logger.info(f"Login attempt for: {username}")
            
            if not username or not password:
                logger.warning(f"Login failed - missing credentials for: {username}")
                return Response({
                    'success': False,
                    'error': 'Kullanıcı adı ve şifre gereklidir',
                    'non_field_errors': ['Kullanıcı adı ve şifre gereklidir']
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Authenticate user
            user = authenticate(username=username, password=password)
            
            if user is None:
                logger.warning(f"Login failed - invalid credentials for: {username}")
                return Response({
                    'success': False,
                    'error': 'Geçersiz kullanıcı adı veya şifre',
                    'non_field_errors': ['Geçersiz kullanıcı adı veya şifre']
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not user.is_active:
                logger.warning(f"Login failed - inactive user: {username}")
                return Response({
                    'success': False,
                    'error': 'Hesabınız devre dışı bırakılmış',
                    'non_field_errors': ['Hesabınız devre dışı bırakılmış']
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get or create token
            token, created = Token.objects.get_or_create(user=user)
            
            logger.info(f"Login successful for: {username}")
            
            # Return success response with consistent format
            return Response({
                'success': True,
                'token': token.key,
                'user_id': user.pk,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                # Include all user data that the frontend expects
                'id': user.pk,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Giriş işlemi sırasında bir hata oluştu',
                'detail': str(e) if settings.DEBUG else 'Sunucu hatası'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    Enhanced API endpoint for viewing and updating the current user's profile
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            logger.info(f"Profile fetch for: {user.username}")
            
            return Response({
                'success': True,
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Profil bilgileri alınırken hata oluştu',
                'detail': str(e) if settings.DEBUG else 'Sunucu hatası'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            logger.info(f"Profile update for: {user.username}")
            
            serializer = self.get_serializer(user, data=request.data, partial=True)
            
            if not serializer.is_valid():
                logger.warning(f"Profile update validation failed: {serializer.errors}")
                return Response({
                    'success': False,
                    'error': serializer.errors,
                    **serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            updated_user = serializer.save()
            logger.info(f"Profile updated successfully for: {updated_user.username}")
            
            return Response({
                'success': True,
                'id': updated_user.id,
                'username': updated_user.username,
                'email': updated_user.email,
                'first_name': updated_user.first_name,
                'last_name': updated_user.last_name,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Profil güncellenirken hata oluştu',
                'detail': str(e) if settings.DEBUG else 'Sunucu hatası'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Enhanced API endpoint for user logout and token deletion
    """
    try:
        user = request.user
        logger.info(f"Logout for: {user.username}")
        
        # Delete the user's token
        if hasattr(user, 'auth_token'):
            user.auth_token.delete()
            logger.info(f"Token deleted for: {user.username}")
        
        return Response({
            'success': True,
            'detail': 'Başarıyla çıkış yapıldı'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Çıkış işlemi sırasında hata oluştu',
            'detail': str(e) if settings.DEBUG else 'Sunucu hatası'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Enhanced API endpoint for changing password
    """
    try:
        user = request.user
        logger.info(f"Password change attempt for: {user.username}")
        
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            logger.warning(f"Password change validation failed: {serializer.errors}")
            return Response({
                'success': False,
                'error': serializer.errors,
                **serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set the new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Update token (invalidate old sessions)
        if hasattr(user, 'auth_token'):
            user.auth_token.delete()
        token, created = Token.objects.get_or_create(user=user)
        
        logger.info(f"Password changed successfully for: {user.username}")
        
        return Response({
            'success': True,
            'detail': 'Şifre başarıyla değiştirildi',
            'token': token.key  # New token for continued authentication
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Şifre değiştirme sırasında hata oluştu',
            'detail': str(e) if settings.DEBUG else 'Sunucu hatası'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Health check endpoint for debugging
@api_view(['GET'])
@permission_classes([AllowAny])
def auth_health_check(request):
    """
    Simple health check endpoint for authentication system
    """
    try:
        user_count = User.objects.count()
        token_count = Token.objects.count()
        
        return Response({
            'status': 'healthy',
            'users': user_count,
            'tokens': token_count,
            'timestamp': timezone.now(),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)