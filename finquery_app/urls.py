from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from finquery_app.interfaces.api.views import QueryViewSet, ChatSessionViewSet, AnalyticsViewSet, stream_query, debug_auth

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

router = DefaultRouter()
router.register(r'query', QueryViewSet, basename='query')
router.register(r'sessions', ChatSessionViewSet, basename='sessions')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/debug/', debug_auth, name='auth_debug'),
    path('query/stream/', stream_query, name='stream_query'),
    path('', include(router.urls)),
]
