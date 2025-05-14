# api/views_user.py - Enhanced Authentication
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from .serializers import UserSerializer, UserRegistrationSerializer, ChangePasswordSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny  # AllowAny'i burada içe aktarın


# views_user.py dosyasında RegisterView sınıfına şunu ekleyin
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is None and isinstance(exc, Exception):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response


# api/views_user.py dosyasına ekleyin (mevcut içeriğin altına)

# Özel hata yakalama fonksiyonu
def handle_exception(exc):
    """Genel hata durumlarını JSON yanıtlarına dönüştürür"""
    from rest_framework.response import Response
    from rest_framework import status
    
    if hasattr(exc, 'detail'):
        # DRF hatası
        return Response({'detail': str(exc.detail)}, status=exc.status_code)
    else:
        # Genel hata
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# RegisterView sınıfını güncelle
class RegisterView(generics.CreateAPIView):
    """
    API endpoint for new user registration
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]  # Herkese açık erişim

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Create token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Tüm hataları yakala ve JSON yanıtlarına dönüştür
            return handle_exception(e)
class CustomAuthToken(ObtainAuthToken):
    """
    Token-based login endpoint
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        })

class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for viewing and updating the current user's profile
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    API endpoint for user logout and token deletion
    """
    if hasattr(request.user, 'auth_token'):
        request.user.auth_token.delete()
    return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    API endpoint for changing password
    """
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        # Set the new password
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        # Update token
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        token, created = Token.objects.get_or_create(user=request.user)
        
        return Response({
            'detail': 'Password updated successfully',
            'token': token.key
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)