from rest_framework.routers import DefaultRouter
from .views import SymptomViewSet,MoodLogViewSet,export_health_report
from .dashboard import DashboardView
from django.urls import path, include

router = DefaultRouter()
router.register(r'symptoms', SymptomViewSet, basename='symptoms')
router.register(r'moods',MoodLogViewSet,basename='moods')

urlpatterns = [
    path('dashboard/',DashboardView.as_view(),name='dashboard'),
    path('reports/export/',export_health_report,name='export-health-report'),
    
]+router.urls