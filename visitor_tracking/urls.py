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

