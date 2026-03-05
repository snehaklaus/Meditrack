from rest_framework import viewsets, filters
from rest_framework.decorators import action, api_view,permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Max
from datetime import date, timedelta
from django.core.cache import cache
from .models import Symptom,Moodlog
from .serializers import SymptomSerializer, SymptomSummarySerializer,MoodLogSerializer
from accounts.permissions import IsOwnerOrDoctor
from .ai_service import HealthInsightsAI
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from .reports import generate_health_report
from rest_framework.permissions import IsAuthenticated, IsAdminUser

class SymptomViewSet(viewsets.ModelViewSet):
    serializer_class = SymptomSerializer
    permission_classes = [IsAuthenticated,IsOwnerOrDoctor]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'severity', 'date']
    search_fields = ['name', 'notes']
    ordering_fields = ['date', 'severity', 'logged_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Symptom.objects.filter(user=user)
        elif user.role == 'doctor':
            patient_ids = user.assigned_patients.values_list('id', flat=True)
            return Symptom.objects.filter(user_id__in=patient_ids)
        return Symptom.objects.none()
    
    @action(detail=False, methods=['get'])
    def last_seven_days(self, request):
        """Get symptoms from last 7 days"""
        seven_days_ago = date.today() - timedelta(days=7)
        queryset = self.get_queryset().filter(date__gte=seven_days_ago)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get aggregated symptom summary"""
        queryset = self.get_queryset().values('name').annotate(
            avg_severity=Avg('severity'),
            count=Count('id'),
            last_occurrence=Max('date')
        )
        serializer = SymptomSummarySerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_medication(self, request):
        """Group symptoms by related medications"""
        medication_id = request.query_params.get('medication_id')
        if medication_id:
            queryset = self.get_queryset().filter(related_medications__id=medication_id)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return Response({"error": "medication_id parameter required"}, status=400)
    
    @action(detail=False, methods=['get'])
    def ai_insights(self, request):
        """Get AI-powered health insights"""
        user = request.user
        #safe days parsing
        try:
            days = int(request.query_params.get('days', 7))
        except (TypeError, ValueError):
            days = 7
        
         # Dynamic Cache key (auto refresh when new symptoms added)
        latest_symptom = self.get_queryset().order_by('-logged_at').first()
        latest_ts = latest_symptom.logged_at.timestamp() if latest_symptom else 0

        cache_key = f"ai_insights_{user.id}_{days}_{latest_ts}"

        # Check cache first (avoid repeated API calls)
        cached_insights = cache.get(cache_key)
        if cached_insights:
            cached_insights['cached'] = True
            return Response(cached_insights)
        
        # Generate new insights
        ai = HealthInsightsAI()
        insights = ai.analyze_symptoms(user, days)
        
        # Only cache successful responses (not errors)
        if 'error' not in insights:
            cache.set(cache_key, insights, 60 * 60 * 6)  # Cache for 6 hours
        
        insights['cached'] = False
        
        return Response(insights)
    
class MoodLogViewSet(viewsets.ModelViewSet):
    serializer_class=MoodLogSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        return Moodlog.objects.filter(user=self.request.user)
    
    @action(detail=False,methods=['get'])
    def trends(self,request):
        """Get mood trends formatted for Chart.js"""
        days = int(request.query_params.get('days',30))
        start_date=date.today()-timedelta(days=days)

        moods=self.get_queryset().filter(
            date__gte=start_date
        ).order_by('date')

        return Response({
            "labels":[m.date.strftime('%Y-%m-%d') for m in moods],
            "datasets":[{
                "label":"Mood",
                "data":[m.mood for m in moods],
                "borderColor":"rgb(153,102,255)",
                "tension":0.1
            }]
        })
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_health_report(request):
    try:
        days=int(request.query_params.get('days',30))
        days=max(1,min(days,365))
    except (TypeError,ValueError):
        days=30

    if request.user.role=='doctor':
        from rest_framework.response import Response
        from rest_framework import status
        return Response(
            {'error':'Doctor cannot export personal health reports.'},
            status=status.HTTP_403_FORBIDDEN
        )
    pdf_bytes=generate_health_report(request.user,days=days)
    filename=f'meditrack_report_{request.user.username}_{days}days.pdf'
    response=HttpResponse(pdf_bytes,content_type='application/pdf')
    response['Content-Disposition']=f'attachment; filename="{filename}"'
    response['Content-Length']=len(pdf_bytes)
    return response

@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_weekly_digest(request):
    from medications.tasks import send_weekly_digest
    send_weekly_digest.delay()  # ← runs in Celery worker, not in web request
    return Response({'result': 'Weekly digest queued successfully'})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def test_email(request):
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    try:
        email = EmailMultiAlternatives(
            subject='MediTrack Test Email',
            body='This is a test email from MediTrack.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['snaik0704@gmail.com'],
        )
        email.send(fail_silently=False)
        return Response({
            'result': 'Email sent successfully!',
            'backend': settings.EMAIL_BACKEND,
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT,
            'user': settings.EMAIL_HOST_USER,
        })
    except Exception as e:
        return Response({
            'error': str(e),
            'backend': settings.EMAIL_BACKEND,
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT,
            'user': settings.EMAIL_HOST_USER,
        }, status=500)