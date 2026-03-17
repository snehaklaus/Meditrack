# meditrack/visitor_tracking/tasks.py

from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from .models import Visitor, VisitorAnalytics, VisitorSession
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_daily_analytics(self):
    """
    Generate daily visitor analytics summary.
    Aggregates visitor data for the previous day.
    
    Scheduled to run at 00:05 UTC every day.
    """
    
    try:
        # Get yesterday's date
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Skip if analytics already exist for this day
        if VisitorAnalytics.objects.filter(date=yesterday).exists():
            logger.info(f"Analytics for {yesterday} already exist, skipping...")
            return
        
        # Get all visitors from yesterday (excluding admin IPs)
        visitors = Visitor.objects.filter(
            timestamp__date=yesterday,
            is_admin_ip=False
        )
        
        if not visitors.exists():
            logger.info(f"No visitors for {yesterday}, skipping...")
            return
        
        # Calculate statistics
        unique_visitors = visitors.values('ip_address').distinct().count()
        total_visits = visitors.count()
        
        # New vs returning visitors
        new_ips = visitors.exclude(
            ip_address__in=Visitor.objects.filter(
                timestamp__date__lt=yesterday,
                is_admin_ip=False
            ).values_list('ip_address', flat=True)
        ).values('ip_address').distinct().count()
        
        returning = unique_visitors - new_ips
        
        # Bot tracking
        bot_visits = visitors.filter(is_bot=True).count()
        human_visits = total_visits - bot_visits
        
        # Geographic data
        countries = visitors.values('country').distinct().count()
        top_country_obj = visitors.values('country').annotate(
            count=Count('id')
        ).order_by('-count').first()
        top_country = top_country_obj['country'] if top_country_obj else None
        
        # Page analytics
        pages_visited = visitors.values('page_visited').distinct().count()
        top_page_obj = visitors.values('page_visited').annotate(
            count=Count('id')
        ).order_by('-count').first()
        top_page = top_page_obj['page_visited'] if top_page_obj else None
        
        # Average session duration
        sessions = VisitorSession.objects.filter(
            first_visit__date=yesterday,
            is_admin_ip=False
        )
        
        if sessions.exists():
            avg_duration = int(sessions.aggregate(
                avg_duration=Count('duration_seconds')
            )['avg_duration'] or 0)
        else:
            avg_duration = 0
        
        # User categories
        admin_visits = Visitor.objects.filter(
            timestamp__date=yesterday,
            is_admin_ip=True
        ).count()
        
        user_visits = visitors.filter(is_authenticated=True).count()
        anonymous_visits = total_visits - user_visits
        
        # Create or update analytics
        analytics, created = VisitorAnalytics.objects.update_or_create(
            date=yesterday,
            defaults={
                'unique_visitors': unique_visitors,
                'total_visits': total_visits,
                'new_visitors': new_ips,
                'returning_visitors': returning,
                'bot_visits': bot_visits,
                'human_visits': human_visits,
                'countries_represented': countries,
                'top_country': top_country,
                'top_page': top_page,
                'pages_visited': pages_visited,
                'average_session_duration': avg_duration,
                'admin_visits': admin_visits,
                'user_visits': user_visits,
                'anonymous_visits': anonymous_visits,
            }
        )
        
        status = 'Created' if created else 'Updated'
        logger.info(
            f"{status} analytics for {yesterday}: "
            f"{unique_visitors} unique visitors, {total_visits} total visits"
        )
        
        return {
            'status': status,
            'date': str(yesterday),
            'unique_visitors': unique_visitors,
            'total_visits': total_visits,
        }
    
    except Exception as exc:
        logger.error(f"Error generating daily analytics: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def cleanup_old_visitors(self):
    """
    Delete visitor records older than 90 days.
    Keeps only recent data to manage database size.
    
    Scheduled to run at 02:00 UTC every week (Sunday).
    """
    
    try:
        # Calculate cutoff date (90 days ago)
        cutoff_date = timezone.now() - timedelta(days=90)
        
        # Delete old visitors
        old_count, _ = Visitor.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        
        logger.info(f"Deleted {old_count} visitor records older than 90 days")
        
        return {
            'status': 'success',
            'deleted_count': old_count,
            'cutoff_date': str(cutoff_date),
        }
    
    except Exception as exc:
        logger.error(f"Error cleaning up old visitors: {str(exc)}")
        raise self.retry(exc=exc, countdown=3600)


@shared_task(bind=True, max_retries=3)
def cleanup_old_sessions(self):
    """
    Delete visitor sessions older than 30 days.
    
    Scheduled to run at 02:30 UTC every week (Sunday).
    """
    
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Delete old sessions
        old_count, _ = VisitorSession.objects.filter(
            last_visit__lt=cutoff_date
        ).delete()
        
        logger.info(f"Deleted {old_count} visitor sessions older than 30 days")
        
        return {
            'status': 'success',
            'deleted_count': old_count,
            'cutoff_date': str(cutoff_date),
        }
    
    except Exception as exc:
        logger.error(f"Error cleaning up old sessions: {str(exc)}")
        raise self.retry(exc=exc, countdown=3600)


@shared_task(bind=True, max_retries=3)
def send_daily_analytics_report(self):
    """
    Send daily analytics summary email to admin.
    
    Scheduled to run at 08:00 UTC every day.
    """
    
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Get yesterday's analytics
        yesterday = timezone.now().date() - timedelta(days=1)
        
        analytics = VisitorAnalytics.objects.filter(date=yesterday).first()
        
        if not analytics:
            logger.warning(f"No analytics found for {yesterday}")
            return
        
        # Get admin email
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if not admin_email:
            logger.warning("ADMIN_EMAIL not configured")
            return
        
        # Calculate engagement rate
        if analytics.unique_visitors > 0:
            engagement_rate = round(
                (analytics.returning_visitors / analytics.unique_visitors) * 100, 1
            )
        else:
            engagement_rate = 0
        
        # Calculate bot percentage
        if analytics.total_visits > 0:
            bot_percentage = round(
                (analytics.bot_visits / analytics.total_visits) * 100, 1
            )
        else:
            bot_percentage = 0
        
        # Build email content
        subject = f"MediTrack Analytics Report - {yesterday.strftime('%Y-%m-%d')}"
        
        html_message = f"""
        <h2>MediTrack Daily Analytics Report</h2>
        <p><strong>Date:</strong> {yesterday.strftime('%B %d, %Y')}</p>
        
        <h3>🎯 Visitor Overview</h3>
        <ul>
            <li><strong>Unique Visitors:</strong> {analytics.unique_visitors}</li>
            <li><strong>Total Visits:</strong> {analytics.total_visits}</li>
            <li><strong>New Visitors:</strong> {analytics.new_visitors}</li>
            <li><strong>Returning Visitors:</strong> {analytics.returning_visitors} ({engagement_rate}%)</li>
        </ul>
        
        <h3>🤖 Bot vs Human Traffic</h3>
        <ul>
            <li><strong>Human Visits:</strong> {analytics.human_visits}</li>
            <li><strong>Bot Visits:</strong> {analytics.bot_visits} ({bot_percentage}%)</li>
        </ul>
        
        <h3>🌍 Geographic Data</h3>
        <ul>
            <li><strong>Countries:</strong> {analytics.countries_represented}</li>
            <li><strong>Top Country:</strong> {analytics.top_country or 'N/A'}</li>
        </ul>
        
        <h3>📄 Page Analytics</h3>
        <ul>
            <li><strong>Pages Visited:</strong> {analytics.pages_visited}</li>
            <li><strong>Top Page:</strong> {analytics.top_page or 'N/A'}</li>
            <li><strong>Average Session Duration:</strong> {analytics.average_session_duration // 60}m {analytics.average_session_duration % 60}s</li>
        </ul>
        
        <h3>👥 User Categories</h3>
        <ul>
            <li><strong>Authenticated Users:</strong> {analytics.user_visits}</li>
            <li><strong>Anonymous Users:</strong> {analytics.anonymous_visits}</li>
        </ul>
        
        <p><a href="https://meditrack.up.railway.app/admin/">View Full Analytics Dashboard</a></p>
        """
        
        # Send email
        send_mail(
            subject,
            'See HTML version',  # Plain text fallback
            settings.DEFAULT_FROM_EMAIL,
            [admin_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Analytics report sent to {admin_email} for {yesterday}")
        
        return {
            'status': 'success',
            'date': str(yesterday),
            'recipient': admin_email,
        }
    
    except Exception as exc:
        logger.error(f"Error sending analytics report: {str(exc)}")
        raise self.retry(exc=exc, countdown=3600)