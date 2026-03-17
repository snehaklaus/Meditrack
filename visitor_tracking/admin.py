# meditrack/visitor_tracking/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from datetime import timedelta
from django.utils import timezone
from .models import Visitor, VisitorSession, VisitorAnalytics, AdminIPWhitelist


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing visitor records.
    """
    
    list_display = [
        'ip_address_display',
        'page_title_display',
        'user_display',
        'country_display',
        'device_type_display',
        'bot_status',
        'timestamp_display',
    ]
    
    list_filter = [
        'is_bot',
        'is_authenticated',
        'country',
        'timestamp',
        'method',
        'status_code',
    ]
    
    search_fields = [
        'ip_address',
        'page_visited',
        'country',
        'user__username',
        'referer',
    ]
    
    # Enable bulk actions including delete
    actions = ['delete_selected', 'delete_admin_visits', 'delete_bot_visits']
    
    readonly_fields = [
        'ip_address',
        'user_agent',
        'referer',
        'page_visited',
        'method',
        'status_code',
        'country',
        'city',
        'latitude',
        'longitude',
        'user',
        'is_authenticated',
        'is_admin_ip',
        'is_bot',
        'session_id',
        'timestamp',
        'user_agent_display',
        'location_map_link',
    ]
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'ip_address',
                'page_visited',
                'method',
                'status_code',
                'referer',
                'timestamp',
            )
        }),
        ('User Agent & Device', {
            'fields': ('user_agent_display',)
        }),
        ('User Information', {
            'fields': ('user', 'is_authenticated')
        }),
        ('Geolocation', {
            'fields': (
                'country',
                'city',
                'latitude',
                'longitude',
                'location_map_link',
            ),
            'classes': ('collapse',)
        }),
        ('Bot & Admin Detection', {
            'fields': ('is_bot', 'is_admin_ip'),
            'classes': ('collapse',)
        }),
        ('Session Tracking', {
            'fields': ('session_id',),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """Disable adding new visitor records manually."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting visitor records."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing visitor records."""
        return False
    
    def ip_address_display(self, obj):
        """Display IP address with color coding."""
        if obj.is_admin_ip:
            color = '#ff9999'
            label = '👤 Admin'
        elif obj.is_bot:
            color = '#ffcc99'
            label = '🤖 Bot'
        else:
            color = '#99ff99'
            label = '👥 User'
        
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color,
            obj.ip_address,
            label
        )
    ip_address_display.short_description = 'IP Address'
    
    def page_title_display(self, obj):
        """Display page with readable title."""
        from .utils import get_page_title
        page_title = get_page_title(obj.page_visited)
        return format_html(
            '<a href="{}" target="_blank">{}</a><br><small>{}</small>',
            obj.page_visited,
            page_title,
            obj.page_visited
        )
    page_title_display.short_description = 'Page'
    
    def user_display(self, obj):
        """Display user with link to user detail."""
        if obj.user:
            # Try to find the correct admin URL for custom user model
            try:
                # For custom user model (accounts.User)
                url = reverse('admin:accounts_user_change', args=[obj.user.id])
            except:
                try:
                    # Fallback to default auth.User
                    url = reverse('admin:auth_user_change', args=[obj.user.id])
                except:
                    # If neither works, just display the username without link
                    return format_html('{} (ID: {})', obj.user.username, obj.user.id)
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.username
            )
        return format_html(
            '<span style="color: #999;">Anonymous</span>'
        )
    user_display.short_description = 'User'
    
    def country_display(self, obj):
        """Display country with flag emoji."""
        if not obj.country:
            return format_html('<span style="color: #999;">Unknown</span>')
        
        # Simple country flag mapping (basic)
        flag_map = {
            'United States': '🇺🇸',
            'India': '🇮🇳',
            'United Kingdom': '🇬🇧',
            'Canada': '🇨🇦',
            'Australia': '🇦🇺',
        }
        
        flag = flag_map.get(obj.country, '🌍')
        return format_html('{} {}', flag, obj.country)
    country_display.short_description = 'Country'
    
    def device_type_display(self, obj):
        """Display device type with icon."""
        from .utils import parse_user_agent
        device_type = parse_user_agent(obj.user_agent)
        
        icons = {
            'Mobile': '📱',
            'Tablet': '📱',
            'Desktop': '🖥️',
        }
        
        icon = icons.get(device_type, '?')
        return format_html('{} {}', icon, device_type)
    device_type_display.short_description = 'Device'
    
    def bot_status(self, obj):
        """Display bot status."""
        if obj.is_bot:
            return format_html(
                '<span style="color: #ff6666; font-weight: bold;">🤖 Bot</span>'
            )
        return format_html(
            '<span style="color: #66ff66; font-weight: bold;">👥 Human</span>'
        )
    bot_status.short_description = 'Type'
    
    def timestamp_display(self, obj):
        """Display timestamp with relative time."""
        from django.utils.timesince import timesince
        return format_html(
            '{}<br><small style="color: #999;">{} ago</small>',
            obj.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            timesince(obj.timestamp)
        )
    timestamp_display.short_description = 'Time'
    
    def user_agent_display(self, obj):
        """Display user agent in readonly field."""
        return format_html(
            '<code style="word-break: break-all; background-color: #f5f5f5; padding: 10px; display: block; border-radius: 3px;">{}</code>',
            obj.user_agent
        )
    
    def location_map_link(self, obj):
        """Generate Google Maps link for coordinates."""
        if obj.latitude and obj.longitude:
            url = f"https://maps.google.com/?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank">View on Google Maps 🗺️</a>',
                url
            )
        return format_html('<span style="color: #999;">Coordinates not available</span>')
    location_map_link.short_description = 'Map'
    
    def delete_admin_visits(self, request, queryset):
        """Custom action to delete admin visits."""
        count = queryset.filter(page_visited__startswith='/admin/').delete()[0]
        self.message_user(request, f'✓ Deleted {count} admin visits')
    delete_admin_visits.short_description = 'Delete selected admin visits (/admin/*)'
    
    def delete_bot_visits(self, request, queryset):
        """Custom action to delete bot visits."""
        count = queryset.filter(is_bot=True).delete()[0]
        self.message_user(request, f'✓ Deleted {count} bot visits')
    delete_bot_visits.short_description = 'Delete selected bot visits'
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of visitor records."""
        return True


@admin.register(VisitorSession)
class VisitorSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing visitor sessions.
    Sessions group multiple visits from same IP/user agent.
    """
    
    list_display = [
        'session_id_display',
        'ip_address',
        'user_display',
        'country_display',
        'page_count_display',
        'duration_display',
        'visits_timeframe',
    ]
    
    list_filter = [
        'country',
        'first_visit',
        'last_visit',
    ]
    
    search_fields = [
        'ip_address',
        'session_id',
        'user__username',
        'country',
    ]
    
    readonly_fields = [
        'session_id',
        'ip_address',
        'user',
        'first_visit',
        'last_visit',
        'page_count',
        'duration_seconds',
        'user_agent',
        'country',
        'city',
    ]
    
    fieldsets = (
        ('Session Information', {
            'fields': (
                'session_id',
                'ip_address',
                'user',
                'first_visit',
                'last_visit',
            )
        }),
        ('Activity', {
            'fields': (
                'page_count',
                'duration_seconds',
            )
        }),
        ('Device Information', {
            'fields': ('user_agent',),
            'classes': ('collapse',)
        }),
        ('Geolocation', {
            'fields': ('country', 'city'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-last_visit']
    date_hierarchy = 'last_visit'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def session_id_display(self, obj):
        """Display session ID (truncated)."""
        return obj.session_id[:12] + '...'
    session_id_display.short_description = 'Session ID'
    
    def user_display(self, obj):
        """Display user with link."""
        if obj.user:
            # Try to find the correct admin URL for custom user model
            try:
                # For custom user model (accounts.User)
                url = reverse('admin:accounts_user_change', args=[obj.user.id])
            except:
                try:
                    # Fallback to default auth.User
                    url = reverse('admin:auth_user_change', args=[obj.user.id])
                except:
                    # If neither works, just display the username without link
                    return format_html('{} (ID: {})', obj.user.username, obj.user.id)
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return format_html('<span style="color: #999;">Anonymous</span>')
    user_display.short_description = 'User'
    
    def country_display(self, obj):
        """Display country with flag."""
        if not obj.country:
            return format_html('<span style="color: #999;">Unknown</span>')
        return format_html('🌍 {}', obj.country)
    country_display.short_description = 'Country'
    
    def page_count_display(self, obj):
        """Display page count with color coding."""
        if obj.page_count > 10:
            color = '#66ff66'
            label = 'High'
        elif obj.page_count > 5:
            color = '#ffff66'
            label = 'Medium'
        else:
            color = '#ffcc99'
            label = 'Low'
        
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px;">{} pages ({})</span>',
            color,
            obj.page_count,
            label
        )
    page_count_display.short_description = 'Pages Visited'
    
    def duration_display(self, obj):
        """Display session duration."""
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        return f"{minutes}m {seconds}s"
    duration_display.short_description = 'Duration'
    
    def visits_timeframe(self, obj):
        """Display when user visited."""
        from django.utils.timesince import timesince
        return format_html(
            '{} - {} ago<br><small>{} minutes active</small>',
            obj.first_visit.strftime('%H:%M:%S'),
            timesince(obj.last_visit),
            (obj.last_visit - obj.first_visit).total_seconds() // 60
        )
    visits_timeframe.short_description = 'Timeframe'


@admin.register(VisitorAnalytics)
class VisitorAnalyticsAdmin(admin.ModelAdmin):
    """
    Admin interface for daily visitor analytics.
    """
    
    list_display = [
        'date',
        'unique_visitors_display',
        'total_visits_display',
        'engagement_rate_display',
        'top_country_display',
        'bot_percentage_display',
    ]
    
    list_filter = [
        'date',
        'top_country',
    ]
    
    search_fields = [
        'date',
        'top_country',
        'top_page',
    ]
    
    readonly_fields = [
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
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Visitor Counts', {
            'fields': (
                'unique_visitors',
                'total_visits',
                'new_visitors',
                'returning_visitors',
            )
        }),
        ('Bot vs Human', {
            'fields': (
                'bot_visits',
                'human_visits',
            )
        }),
        ('Geographic', {
            'fields': (
                'countries_represented',
                'top_country',
            )
        }),
        ('Page Analytics', {
            'fields': (
                'pages_visited',
                'top_page',
                'average_session_duration',
            )
        }),
        ('User Categories', {
            'fields': (
                'admin_visits',
                'user_visits',
                'anonymous_visits',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-date']
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def unique_visitors_display(self, obj):
        """Display unique visitor count."""
        return format_html(
            '<strong style="font-size: 1.2em; color: #0066cc;">{}</strong>',
            obj.unique_visitors
        )
    unique_visitors_display.short_description = 'Unique Visitors'
    
    def total_visits_display(self, obj):
        """Display total visit count."""
        return format_html(
            '<strong style="font-size: 1.2em; color: #0066cc;">{}</strong>',
            obj.total_visits
        )
    total_visits_display.short_description = 'Total Visits'
    
    def engagement_rate_display(self, obj):
        """Display engagement rate (returning visitors %)."""
        if obj.unique_visitors == 0:
            rate = 0
        else:
            rate = round((obj.returning_visitors / obj.unique_visitors) * 100, 1)
        
        color = '#66ff66' if rate > 30 else '#ffff66' if rate > 10 else '#ffcc99'
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px;">{:.1f}%</span>',
            color,
            rate
        )
    engagement_rate_display.short_description = 'Engagement Rate'
    
    def top_country_display(self, obj):
        """Display top country."""
        return f"🌍 {obj.top_country}" if obj.top_country else "Unknown"
    top_country_display.short_description = 'Top Country'
    
    def bot_percentage_display(self, obj):
        """Display bot traffic percentage."""
        if obj.total_visits == 0:
            percentage = 0
        else:
            percentage = round((obj.bot_visits / obj.total_visits) * 100, 1)
        
        return format_html(
            '<span style="color: #ff9999; font-weight: bold;">🤖 {:.1f}%</span>',
            percentage
        )
    bot_percentage_display.short_description = 'Bot Traffic'


@admin.register(AdminIPWhitelist)
class AdminIPWhitelistAdmin(admin.ModelAdmin):
    """
    Admin interface for managing admin IP addresses.
    """
    
    list_display = [
        'ip_address',
        'user_display',
        'description',
        'is_active_display',
        'added_at',
    ]
    
    list_filter = [
        'is_active',
        'added_at',
    ]
    
    search_fields = [
        'ip_address',
        'description',
        'user__username',
    ]
    
    fieldsets = (
        ('IP Address', {
            'fields': ('ip_address',)
        }),
        ('Details', {
            'fields': (
                'user',
                'description',
                'is_active',
            )
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-added_at']
    date_hierarchy = 'added_at'
    
    def user_display(self, obj):
        """Display user with link."""
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return format_html('<span style="color: #999;">Not assigned</span>')
    user_display.short_description = 'User'
    
    def is_active_display(self, obj):
        """Display active status with color."""
        if obj.is_active:
            return format_html(
                '<span style="color: #66ff66; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: #ff6666; font-weight: bold;">✗ Inactive</span>'
        )
    is_active_display.short_description = 'Status'