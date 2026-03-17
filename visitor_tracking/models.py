# meditrack/visitor_tracking/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

class Visitor(models.Model):
    """
    Model to track all website visitors.
    Excludes admin IP addresses as configured in settings.
    """
    
    # IP and identification
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField()
    referer = models.CharField(max_length=500, null=True, blank=True)
    
    # Request details
    page_visited = models.CharField(max_length=500, db_index=True)
    method = models.CharField(max_length=10, default='GET')
    status_code = models.IntegerField(default=200)
    
    # Geolocation (optional, populated via MaxMind GeoIP2)
    country = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # User tracking
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='visits'
    )
    is_authenticated = models.BooleanField(default=False)
    
    # Admin tracking
    is_admin_ip = models.BooleanField(default=False, db_index=True)
    is_bot = models.BooleanField(default=False)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Session tracking
    session_id = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'is_admin_ip']),
            models.Index(fields=['page_visited', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['country', 'timestamp']),
        ]
        verbose_name = 'Visitor'
        verbose_name_plural = 'Visitors'
    
    def __str__(self):
        return f"{self.ip_address} - {self.page_visited} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class VisitorSession(models.Model):
    """
    Tracks visitor sessions for analytics.
    Groups multiple visits from same IP/user agent into sessions.
    """
    
    ip_address = models.GenericIPAddressField(db_index=True)
    session_id = models.CharField(max_length=200, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='visitor_sessions'
    )
    
    # Session tracking
    first_visit = models.DateTimeField(auto_now_add=True)
    last_visit = models.DateTimeField(auto_now=True)
    page_count = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(default=0)
    
    is_admin_ip = models.BooleanField(default=False)
    user_agent = models.TextField()
    
    # Geolocation
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-last_visit']
        indexes = [
            models.Index(fields=['ip_address', 'last_visit']),
            models.Index(fields=['session_id', 'last_visit']),
        ]
    
    def __str__(self):
        duration = (self.last_visit - self.first_visit).total_seconds()
        return f"Session {self.session_id} - {self.ip_address} - {self.page_count} pages"


class VisitorAnalytics(models.Model):
    """
    Daily aggregated visitor statistics.
    Used for performance optimization and trend analysis.
    """
    
    date = models.DateField(unique=True, db_index=True)
    
    # Visitor counts
    unique_visitors = models.IntegerField(default=0)
    total_visits = models.IntegerField(default=0)
    new_visitors = models.IntegerField(default=0)
    returning_visitors = models.IntegerField(default=0)
    
    # Bot tracking
    bot_visits = models.IntegerField(default=0)
    human_visits = models.IntegerField(default=0)
    
    # Geographic
    countries_represented = models.IntegerField(default=0)
    top_country = models.CharField(max_length=100, null=True, blank=True)
    
    # Page analytics
    top_page = models.CharField(max_length=500, null=True, blank=True)
    pages_visited = models.IntegerField(default=0)
    
    # Device info
    average_session_duration = models.IntegerField(default=0)  # in seconds
    
    # Admin tracking
    admin_visits = models.IntegerField(default=0)
    user_visits = models.IntegerField(default=0)
    anonymous_visits = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Daily Visitor Analytics'
        verbose_name_plural = 'Daily Visitor Analytics'
    
    def __str__(self):
        return f"Analytics for {self.date} - {self.unique_visitors} visitors"


class AdminIPWhitelist(models.Model):
    """
    Stores admin IP addresses to exclude from visitor tracking.
    """
    
    ip_address = models.GenericIPAddressField(unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='admin_ips'
    )
    description = models.CharField(max_length=255, blank=True, help_text="e.g., 'Office', 'Home', 'VPN'")
    is_active = models.BooleanField(default=True, db_index=True)
    
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-added_at']
        verbose_name = 'Admin IP Whitelist'
        verbose_name_plural = 'Admin IP Whitelists'
    
    def __str__(self):
        desc = f" - {self.description}" if self.description else ""
        return f"{self.ip_address}{desc}"