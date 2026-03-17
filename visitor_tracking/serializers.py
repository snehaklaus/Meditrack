# meditrack/visitor_tracking/serializers.py

from rest_framework import serializers
from .models import Visitor, VisitorSession, VisitorAnalytics, AdminIPWhitelist


class VisitorSerializer(serializers.ModelSerializer):
    """Serialize individual visitor records."""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    page_title = serializers.SerializerMethodField()
    device_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Visitor
        fields = [
            'id',
            'ip_address',
            'user_agent',
            'referer',
            'page_visited',
            'page_title',
            'method',
            'status_code',
            'country',
            'city',
            'latitude',
            'longitude',
            'user',
            'user_username',
            'is_authenticated',
            'is_bot',
            'device_type',
            'timestamp',
        ]
        read_only_fields = fields
    
    def get_page_title(self, obj):
        """Extract readable page title from path."""
        from .utils import get_page_title
        return get_page_title(obj.page_visited)
    
    def get_device_type(self, obj):
        """Determine device type from user agent."""
        from .utils import parse_user_agent
        return parse_user_agent(obj.user_agent)


class VisitorSessionSerializer(serializers.ModelSerializer):
    """Serialize visitor session data."""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    device_type = serializers.SerializerMethodField()
    
    class Meta:
        model = VisitorSession
        fields = [
            'id',
            'session_id',
            'ip_address',
            'user',
            'user_username',
            'first_visit',
            'last_visit',
            'page_count',
            'duration_seconds',
            'duration_minutes',
            'country',
            'city',
            'device_type',
            'user_agent',
        ]
        read_only_fields = fields
    
    def get_duration_minutes(self, obj):
        """Convert duration seconds to minutes."""
        return round(obj.duration_seconds / 60, 2)
    
    def get_device_type(self, obj):
        """Determine device type from user agent."""
        from .utils import parse_user_agent
        return parse_user_agent(obj.user_agent)


class VisitorAnalyticsSerializer(serializers.ModelSerializer):
    """Serialize daily analytics data."""
    
    engagement_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = VisitorAnalytics
        fields = [
            'id',
            'date',
            'unique_visitors',
            'total_visits',
            'new_visitors',
            'returning_visitors',
            'bot_visits',
            'human_visits',
            'countries_represented',
            'top_country',
            'top_page',
            'pages_visited',
            'average_session_duration',
            'admin_visits',
            'user_visits',
            'anonymous_visits',
            'engagement_rate',
        ]
        read_only_fields = fields
    
    def get_engagement_rate(self, obj):
        """Calculate engagement rate as percentage."""
        if obj.unique_visitors == 0:
            return 0
        return round((obj.returning_visitors / obj.unique_visitors) * 100, 2)


class AdminIPWhitelistSerializer(serializers.ModelSerializer):
    """Serialize admin IP whitelist entries."""
    
    class Meta:
        model = AdminIPWhitelist
        fields = [
            'id',
            'ip_address',
            'user',
            'description',
            'is_active',
            'added_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'added_at', 'updated_at']


class VisitorStatsSerializer(serializers.Serializer):
    """Serialize visitor statistics summary."""
    
    total_visitors = serializers.IntegerField()
    total_visits = serializers.IntegerField()
    unique_ips = serializers.IntegerField()
    authenticated_users = serializers.IntegerField()
    bot_visits = serializers.IntegerField()
    human_visits = serializers.IntegerField()
    most_visited_page = serializers.CharField()
    visitors_from_countries = serializers.IntegerField()
    top_5_countries = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    top_5_pages = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    visits_last_24_hours = serializers.IntegerField()
    visits_last_7_days = serializers.IntegerField()
    visits_last_30_days = serializers.IntegerField()
    average_daily_visitors = serializers.FloatField()
    returning_visitor_percentage = serializers.FloatField()


class DashboardChartDataSerializer(serializers.Serializer):
    """Serialize data for dashboard charts."""
    
    labels = serializers.ListField(child=serializers.CharField())
    data = serializers.ListField(child=serializers.IntegerField())
    colors = serializers.ListField(child=serializers.CharField(), required=False)


class RealtimeVisitorSerializer(serializers.Serializer):
    """Serialize real-time visitor data."""
    
    active_now = serializers.IntegerField()
    last_5_minutes = serializers.IntegerField()
    last_1_hour = serializers.IntegerField()
    top_pages_now = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    countries_now = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    recent_visits = VisitorSerializer(many=True)