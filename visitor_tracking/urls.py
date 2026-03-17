# meditrack/visitor_tracking/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VisitorViewSet,
    VisitorSessionViewSet,
    VisitorAnalyticsViewSet,
    AdminIPWhitelistViewSet,
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'visitors', VisitorViewSet, basename='visitor')
router.register(r'sessions', VisitorSessionViewSet, basename='visitor-session')
router.register(r'analytics', VisitorAnalyticsViewSet, basename='visitor-analytics')
router.register(r'admin-ips', AdminIPWhitelistViewSet, basename='admin-ip-whitelist')

app_name = 'visitor_tracking'

urlpatterns = [
    path('', include(router.urls)),
]

# Alternative if you want custom URL structure:
# urlpatterns = [
#     # Visitor endpoints
#     path('visitors/', VisitorViewSet.as_view({'get': 'list'}), name='visitor-list'),
#     path('visitors/summary/', VisitorViewSet.as_view({'get': 'summary'}), name='visitor-summary'),
#     path('visitors/realtime/', VisitorViewSet.as_view({'get': 'realtime'}), name='visitor-realtime'),
#     path('visitors/by-country/', VisitorViewSet.as_view({'get': 'by_country'}), name='visitor-by-country'),
#     path('visitors/by-page/', VisitorViewSet.as_view({'get': 'by_page'}), name='visitor-by-page'),
#     path('visitors/trends/', VisitorViewSet.as_view({'get': 'trends'}), name='visitor-trends'),
#     path('visitors/<int:pk>/', VisitorViewSet.as_view({'get': 'retrieve'}), name='visitor-detail'),
#     
#     # Session endpoints
#     path('sessions/', VisitorSessionViewSet.as_view({'get': 'list'}), name='session-list'),
#     path('sessions/<int:pk>/', VisitorSessionViewSet.as_view({'get': 'retrieve'}), name='session-detail'),
#     
#     # Analytics endpoints
#     path('analytics/', VisitorAnalyticsViewSet.as_view({'get': 'list'}), name='analytics-list'),
#     path('analytics/<int:pk>/', VisitorAnalyticsViewSet.as_view({'get': 'retrieve'}), name='analytics-detail'),
#     
#     # Admin IP whitelist
#     path('admin-ips/', AdminIPWhitelistViewSet.as_view({'get': 'list', 'post': 'create'}), name='admin-ip-list'),
#     path('admin-ips/<int:pk>/', AdminIPWhitelistViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='admin-ip-detail'),
#     path('admin-ips/clear-cache/', AdminIPWhitelistViewSet.as_view({'post': 'clear_cache'}), name='admin-ip-clear-cache'),
# ]