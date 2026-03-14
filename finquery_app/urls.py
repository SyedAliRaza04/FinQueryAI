from django.urls import path, include
from rest_framework.routers import DefaultRouter
from finquery_app.interfaces.api.views import QueryViewSet, ChatSessionViewSet, AnalyticsViewSet, stream_query

router = DefaultRouter()
router.register(r'query', QueryViewSet, basename='query')
router.register(r'sessions', ChatSessionViewSet, basename='sessions')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('query/stream/', stream_query, name='stream_query'),
    path('', include(router.urls)),
]
