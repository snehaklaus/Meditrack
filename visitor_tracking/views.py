# meditrack/visitor_tracking/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from .models import Visitor, VisitorSession, VisitorAnalytics, AdminIPWhitelist
from .serializers import (
    VisitorSerializer,
    VisitorSessionSerializer,
    VisitorAnalyticsSerializer,
    AdminIPWhitelistSerializer,
    VisitorStatsSerializer,
    DashboardChartDataSerializer,
    RealtimeVisitorSerializer,
)


class VisitorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only viewset for viewing visitor analytics.
    
    Endpoints:
    - GET /api/analytics/visitors/ - List all visitors (paginated)
    - GET /api/analytics/visitors/{id}/ - Visitor details
    - GET /api/analytics/visitors/summary/ - Overall stats
    - GET /api/analytics/visitors/realtime/ - Real-time data
    - GET /api/analytics/visitors/by-country/ - Visitors by country
    - GET /api/analytics/visitors/by-page/ - Visitors by page
    - GET /api/analytics/visitors/trends/ - Visitor trends
    """
    
    queryset = Visitor.objects.filter(is_admin_ip=False).select_related('user').order_by('-timestamp')
    serializer_class = VisitorSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['country', 'page_visited', 'is_bot', 'is_authenticated']
    search_fields = ['ip_address', 'page_visited', 'country']
    ordering_fields = ['timestamp', 'ip_address', 'country']
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get overall visitor statistics.
        
        Returns total visitors, visits, top pages, top countries, etc.
        """
        
        # Time ranges
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Get statistics
        all_visitors = Visitor.objects.filter(is_admin_ip=False)
        
        stats = {
            'total_visitors': all_visitors.values('ip_address').distinct().count(),
            'total_visits': all_visitors.count(),
            'unique_ips': all_visitors.values('ip_address').distinct().count(),
            'authenticated_users': all_visitors.filter(is_authenticated=True).values('user').distinct().count(),
            'bot_visits': all_visitors.filter(is_bot=True).count(),
            'human_visits': all_visitors.filter(is_bot=False).count(),
            'most_visited_page': all_visitors.values('page_visited').annotate(count=Count('id')).order_by('-count').first(),
            'visitors_from_countries': all_visitors.values('country').distinct().count(),
            'visits_last_24_hours': all_visitors.filter(timestamp__gte=last_24h).count(),
            'visits_last_7_days': all_visitors.filter(timestamp__gte=last_7d).count(),
            'visits_last_30_days': all_visitors.filter(timestamp__gte=last_30d).count(),
        }
        
        # Top 5 countries
        top_countries = all_visitors.values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        stats['top_5_countries'] = [
            {'country': item['country'], 'visits': item['count']}
            for item in top_countries
        ]
        
        # Top 5 pages
        top_pages = all_visitors.values('page_visited').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        stats['top_5_pages'] = [
            {'page': item['page_visited'], 'visits': item['count']}
            for item in top_pages
        ]
        
        # Calculate averages
        days_with_data = all_visitors.values('timestamp__date').distinct().count()
        stats['average_daily_visitors'] = round(
            stats['total_visitors'] / max(days_with_data, 1), 2
        )
        
        stats['returning_visitor_percentage'] = round(
            (all_visitors.values('ip_address').annotate(count=Count('id')).filter(count__gt=1).count() / 
             max(stats['unique_ips'], 1) * 100), 2
        )
        
        serializer = VisitorStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def realtime(self, request):
        """
        Get real-time visitor data (last 5 minutes).
        
        Returns: Active visitors, top pages, countries, recent visits
        """
        
        now = timezone.now()
        last_5min = now - timedelta(minutes=5)
        last_1hour = now - timedelta(hours=1)
        
        recent_visitors = Visitor.objects.filter(
            timestamp__gte=last_5min,
            is_admin_ip=False
        ).order_by('-timestamp')[:20]
        
        data = {
            'active_now': recent_visitors.count(),
            'last_5_minutes': Visitor.objects.filter(
                timestamp__gte=last_5min,
                is_admin_ip=False
            ).count(),
            'last_1_hour': Visitor.objects.filter(
                timestamp__gte=last_1hour,
                is_admin_ip=False
            ).count(),
            'top_pages_now': list(
                Visitor.objects.filter(
                    timestamp__gte=last_5min,
                    is_admin_ip=False
                ).values('page_visited').annotate(count=Count('id')).order_by('-count')[:5]
            ),
            'countries_now': list(
                Visitor.objects.filter(
                    timestamp__gte=last_5min,
                    is_admin_ip=False,
                    country__isnull=False
                ).values('country').annotate(count=Count('id')).order_by('-count')[:5]
            ),
            'recent_visits': VisitorSerializer(recent_visitors, many=True).data,
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def by_country(self, request):
        """Get visitor breakdown by country."""
        
        country = request.query_params.get('country')
        
        visitors = Visitor.objects.filter(
            is_admin_ip=False,
            country=country
        ) if country else Visitor.objects.filter(is_admin_ip=False)
        
        countries = visitors.values('country').annotate(
            count=Count('id')
        ).order_by('-count')
        
        data = {
            'labels': [item['country'] for item in countries],
            'data': [item['count'] for item in countries],
        }
        
        serializer = DashboardChartDataSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_page(self, request):
        """Get visitor breakdown by page."""
        
        pages = Visitor.objects.filter(
            is_admin_ip=False
        ).values('page_visited').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        from .utils import get_page_title
        
        data = {
            'labels': [get_page_title(item['page_visited']) for item in pages],
            'data': [item['count'] for item in pages],
        }
        
        serializer = DashboardChartDataSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """
        Get visitor trends over time (daily).
        
        Query params: days (default: 30)
        """
        
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        analytics = VisitorAnalytics.objects.filter(
            date__gte=start_date
        ).order_by('date')
        
        data = {
            'labels': [str(item.date) for item in analytics],
            'total_visits': [item.total_visits for item in analytics],
            'unique_visitors': [item.unique_visitors for item in analytics],
            'returning_visitors': [item.returning_visitors for item in analytics],
            'bot_visits': [item.bot_visits for item in analytics],
        }
        
        return Response(data)


class VisitorSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only viewset for viewing visitor sessions.
    
    Sessions group multiple visits from the same IP/user agent.
    """
    
    queryset = VisitorSession.objects.filter(is_admin_ip=False).order_by('-last_visit')
    serializer_class = VisitorSessionSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['country', 'user']
    search_fields = ['ip_address', 'session_id', 'country']
    ordering_fields = ['last_visit', 'page_count', 'duration_seconds']


class VisitorAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only viewset for viewing daily analytics.
    """
    
    queryset = VisitorAnalytics.objects.all().order_by('-date')
    serializer_class = VisitorAnalyticsSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['date', 'top_country']
    search_fields = ['top_page', 'top_country']
    ordering_fields = ['date', 'unique_visitors', 'total_visits']


class AdminIPWhitelistViewSet(viewsets.ModelViewSet):
    """
    Admin-only viewset for managing admin IP whitelist.
    
    Endpoints:
    - GET /api/analytics/admin-ips/ - List all admin IPs
    - POST /api/analytics/admin-ips/ - Add new admin IP
    - PUT /api/analytics/admin-ips/{id}/ - Update admin IP
    - DELETE /api/analytics/admin-ips/{id}/ - Remove admin IP
    """
    
    queryset = AdminIPWhitelist.objects.all().order_by('-added_at')
    serializer_class = AdminIPWhitelistSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['is_active']
    search_fields = ['ip_address', 'description']
    
    def perform_create(self, serializer):
        """Set user when creating admin IP."""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def clear_cache(self, request):
        """Clear the admin IP cache."""
        
        from django.core.cache import cache
        
        # Clear all admin IP cache keys
        cache.delete_many([
            f'admin_ip_check_{key}' 
            for key in cache.keys('admin_ip_check_*')
        ])
        
        return Response({'status': 'Admin IP cache cleared'})