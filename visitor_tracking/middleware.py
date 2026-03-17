# meditrack/visitor_tracking/middleware.py

import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache
from .models import Visitor, VisitorSession
from .utils import (
    get_client_ip,
    is_admin_ip,
    is_bot,
    get_client_country,
    should_track_visitor,
    generate_session_id,
    parse_user_agent,
)

logger = logging.getLogger(__name__)


class VisitorTrackingMiddleware(MiddlewareMixin):
    """
    Django middleware to track all page visits.
    
    Features:
    - Tracks IP, user agent, referer, page visited, timestamp
    - Excludes admin IPs
    - Detects bots/crawlers
    - Groups visits into sessions
    - Handles geolocation
    - Caches data for performance
    
    Add to MIDDLEWARE in settings.py:
        'visitor_tracking.middleware.VisitorTrackingMiddleware'
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'ENABLE_VISITOR_TRACKING', True)
    
    def process_request(self, request):
        """
        Called before view is processed.
        Store request data for later tracking.
        """
        
        if not self.enabled:
            return None
        
        # Store data on request object for later use
        request._visitor_ip = get_client_ip(request)
        request._visitor_timestamp = __import__('django.utils.timezone', fromlist=['now']).now()
        request._visitor_user_agent = request.META.get('HTTP_USER_AGENT', '')
        request._visitor_referer = request.META.get('HTTP_REFERER', '')
        
        return None
    
    def process_response(self, request, response):
        """
        Called after view is processed.
        Track the visitor.
        """
        
        if not self.enabled:
            return response
        
        # FIRST: Exclude all admin panel visits - don't track admin paths at all
        if request.path.startswith('/admin/'):
            return response
        
        try:
            # Extract request data
            ip_address = getattr(request, '_visitor_ip', get_client_ip(request))
            user_agent = getattr(request, '_visitor_user_agent', request.META.get('HTTP_USER_AGENT', ''))
            referer = getattr(request, '_visitor_referer', request.META.get('HTTP_REFERER', ''))
            
            # Check if admin
            admin_ip = is_admin_ip(ip_address)
            
            # Only track if not admin
            if admin_ip:
                return response
            
            # Check if bot
            bot = is_bot(user_agent)
            
            # Determine if should track
            if not should_track_visitor(request, ip_address, admin_ip):
                return response
            
            # Create visitor record asynchronously
            # Import here to avoid circular imports
            from django.contrib.auth.models import AnonymousUser
            
            user = request.user if request.user.is_authenticated else None
            session_id = generate_session_id(ip_address, user_agent, user)
            
            # Get geolocation data (always enabled, uses free API)
            country = get_client_country(ip_address)
            
            # Create Visitor record (non-blocking)
            try:
                visitor = Visitor.objects.create(
                    ip_address=ip_address,
                    user_agent=user_agent,
                    referer=referer,
                    page_visited=request.path,
                    method=request.method,
                    status_code=response.status_code,
                    user=user,
                    is_authenticated=request.user.is_authenticated,
                    is_admin_ip=False,  # Already excluded above
                    is_bot=bot,
                    country=country,  # Now a simple string
                    city=None,  # Not available with free API
                    latitude=None,  # Not available with free API
                    longitude=None,  # Not available with free API
                    session_id=session_id,
                )
                
                # Update or create session (pass country as string)
                self._update_visitor_session(ip_address, user_agent, user, session_id, country)
            
            except Exception as e:
                logger.error(f"Error creating visitor record: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in VisitorTrackingMiddleware: {str(e)}")
        
        return response
    
    def _update_visitor_session(self, ip_address, user_agent, user, session_id, geo_data):
        """
        Update or create visitor session.
        Groups multiple visits from same IP/user agent.
        """
        
        try:
            session, created = VisitorSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'ip_address': ip_address,
                    'user': user,
                    'user_agent': user_agent,
                    'is_admin_ip': False,
                    'country': geo_data,  # Now a simple string, not dict
                    'city': None,  # Not available with free API
                }
            )
            
            # Update session page count
            session.page_count += 1
            
            # Calculate duration
            duration = (session.last_visit - session.first_visit).total_seconds()
            session.duration_seconds = int(duration)
            
            session.save()
        
        except Exception as e:
            logger.error(f"Error updating visitor session: {str(e)}")


class BotDetectionMiddleware(MiddlewareMixin):
    """
    Advanced bot detection middleware.
    Marks requests as bot visits for filtering.
    """
    
    def process_request(self, request):
        """Check if request is from a bot."""
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        request.is_bot = is_bot(user_agent)
        
        return None


class RateLimitingMiddleware(MiddlewareMixin):
    """
    Rate limiting to prevent abuse from single IPs.
    Limits: 100 requests per minute per IP.
    """
    
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_PERIOD = 60  # seconds
    
    def process_request(self, request):
        """Check rate limit for IP."""
        
        ip_address = get_client_ip(request)
        cache_key = f'rate_limit_{ip_address}'
        
        # Get current request count
        request_count = cache.get(cache_key, 0)
        
        if request_count >= self.RATE_LIMIT_REQUESTS:
            from django.http import HttpResponse
            return HttpResponse('Rate limit exceeded', status=429)
        
        # Increment counter
        cache.set(cache_key, request_count + 1, self.RATE_LIMIT_PERIOD)
        
        return None