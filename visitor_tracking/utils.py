# meditrack/visitor_tracking/utils.py

import logging
from django.conf import settings
from django.core.cache import cache
from .models import AdminIPWhitelist
import re

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """
    Extract the real client IP address from the request.
    Handles proxy headers like X-Forwarded-For, X-Real-IP, etc.
    
    Priority:
    1. HTTP_X_FORWARDED_FOR (load balancers, proxies)
    2. HTTP_X_REAL_IP (nginx)
    3. HTTP_CF_CONNECTING_IP (Cloudflare)
    4. REMOTE_ADDR (direct connection)
    """
    
    # Check X-Forwarded-For (can contain multiple IPs)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP (client's actual IP)
        ip = x_forwarded_for.split(',')[0].strip()
        return ip
    
    # Check X-Real-IP (nginx, AWS ALB)
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()
    
    # Check Cloudflare
    cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_connecting_ip:
        return cf_connecting_ip.strip()
    
    # Fallback to REMOTE_ADDR (direct connection)
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def is_admin_ip(ip_address):
    """
    Check if IP is in the admin whitelist.
    Caches result for 1 hour to reduce database queries.
    """
    
    cache_key = f'admin_ip_check_{ip_address}'
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        return cached_result
    
    # Check environment variable ADMIN_IPS (comma-separated)
    admin_ips_env = getattr(settings, 'ADMIN_IPS', '')
    if admin_ips_env:
        admin_ips_list = [ip.strip() for ip in admin_ips_env.split(',')]
        is_admin = ip_address in admin_ips_list
        cache.set(cache_key, is_admin, 3600)  # Cache for 1 hour
        return is_admin
    
    # Check database whitelist
    is_admin = AdminIPWhitelist.objects.filter(
        ip_address=ip_address,
        is_active=True
    ).exists()
    
    cache.set(cache_key, is_admin, 3600)
    return is_admin


def is_bot(user_agent):
    """
    Detect if user agent is a bot/crawler.
    Returns True if bot detected, False if human.
    """
    
    if not user_agent:
        return False
    
    user_agent_lower = user_agent.lower()
    
    # Common bot patterns
    bot_patterns = [
        r'bot',
        r'crawler',
        r'spider',
        r'scraper',
        r'curl',
        r'wget',
        r'python',
        r'java[^;]*\)',
        r'googlebot',
        r'bingbot',
        r'yandex',
        r'baidu',
        r'duckduckgo',
        r'baiduspider',
        r'sogou',
        r'slurp',
        r'msagent',
        r'semrush',
        r'ahrefs',
        r'majestic',
        r'mj12bot',
        r'uptimerobot',
        r'pingdom',
        r'statuspage',
        r'phantomjs',
        r'headless',
        r'puppeteer',
        r'selenium',
    ]
    
    for pattern in bot_patterns:
        if re.search(pattern, user_agent_lower):
            return True
    
    return False


def parse_user_agent(user_agent):
    """
    Parse user agent string to extract device type.
    Returns: 'Mobile', 'Tablet', or 'Desktop'
    """
    
    if not user_agent:
        return 'Unknown'
    
    ua_lower = user_agent.lower()
    
    # Mobile detection
    if any(x in ua_lower for x in ['mobile', 'android', 'iphone', 'ipod']):
        return 'Mobile'
    
    # Tablet detection
    if any(x in ua_lower for x in ['tablet', 'ipad', 'kindle', 'playbook']):
        return 'Tablet'
    
    return 'Desktop'


def get_client_country(ip_address):
    """
    Get country from IP address using FREE public API (no credentials needed).
    
    Uses ip-api.com (free tier) or ipapi.co as fallback
    Both are free with no API key required
    
    Returns: Country name string or 'Unknown'
    """
    
    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
        return 'Local'
    
    try:
        import requests
        from django.core.cache import cache
        
        # Check cache first (24 hour TTL to avoid hitting API repeatedly)
        cache_key = f'ip_country_{ip_address}'
        cached_country = cache.get(cache_key)
        if cached_country:
            return cached_country
        
        # Try ip-api.com (free, no API key needed, 45 req/min limit)
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip_address}',
                timeout=3,
                params={'fields': 'country'}
            )
            if response.status_code == 200:
                data = response.json()
                country = data.get('country', 'Unknown')
                if country and country != 'Unknown':
                    # Cache for 24 hours
                    cache.set(cache_key, country, 86400)
                    return country
        except Exception as e:
            logger.debug(f"ip-api.com lookup failed: {str(e)}")
        
        # Fallback: Try ipapi.co (free, no key needed)
        try:
            response = requests.get(
                f'https://ipapi.co/{ip_address}/json/',
                timeout=3,
                headers={'Accept': 'application/json'}
            )
            if response.status_code == 200:
                data = response.json()
                country = data.get('country_name', 'Unknown')
                if country and country != 'Unknown':
                    # Cache for 24 hours
                    cache.set(cache_key, country, 86400)
                    return country
        except Exception as e:
            logger.debug(f"ipapi.co lookup failed: {str(e)}")
        
        return 'Unknown'
        
    except Exception as e:
        logger.warning(f"Country lookup failed for {ip_address}: {str(e)}")
        return 'Unknown'


def should_track_visitor(request, ip_address, is_admin):
    """
    Determine if this request should be tracked.
    Excludes: admin IPs, static files, media, health checks
    """
    
    path = request.path
    
    # Exclude static and media files
    if path.startswith('/static/') or path.startswith('/media/'):
        return False
    
    # Exclude health checks
    if path in ['/health/', '/healthz/', '/ping/']:
        return False
    
    # Exclude admin IPs
    if is_admin:
        return False
    
    # Exclude certain status codes
    return True


def generate_session_id(ip_address, user_agent, user=None):
    """
    Generate a unique session ID for visitor.
    Combines IP, user agent, and user ID (if authenticated).
    """
    
    import hashlib
    
    session_string = f"{ip_address}:{user_agent}:{user.id if user else 'anon'}"
    session_hash = hashlib.md5(session_string.encode()).hexdigest()
    
    return session_hash


def is_new_visitor(ip_address):
    """
    Check if IP address is visiting for the first time.
    """
    
    from .models import Visitor
    
    return not Visitor.objects.filter(
        ip_address=ip_address,
        is_admin_ip=False
    ).exists()


def get_page_title(path):
    """
    Extract page title from URL path for better readability in analytics.
    """
    
    path_map = {
        '/': 'Landing Page',
        '/api/auth/login/': 'Login',
        '/api/auth/register/': 'Register',
        '/api/auth/profile/': 'Profile',
        '/api/medications/': 'Medications',
        '/api/symptoms/': 'Symptoms',
        '/api/moods/': 'Mood Tracking',
        '/api/dashboard/': 'Dashboard',
        '/api/reports/export/': 'Health Report',
        '/api/symptoms/ai_insights/': 'AI Insights',
        '/fhir/r4/': 'FHIR API',
    }
    
    for pattern, title in path_map.items():
        if pattern in path:
            return title
    
    return path