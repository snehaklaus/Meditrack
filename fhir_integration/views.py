# fhir_integration/views.py
"""
FHIR R4 API Views - RESTful endpoints for FHIR resources
Implements read-only access to Patient, Medication, MedicationStatement, Observation resources
"""
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from accounts.models import User
from medications.models import Medication
from symptoms.models import Symptom, Moodlog
from .serializers import (
    FHIRPatientSerializer,
    FHIRMedicationSerializer,
    FHIRObservationSerializer,
    FHIRMoodObservationSerializer
)
import logging

logger = logging.getLogger('fhir_integration')


class FHIRBaseViewSet(viewsets.ViewSet):
    """Base class for FHIR ViewSets with common functionality"""
    permission_classes = [IsAuthenticated]
    
    def get_bundle_response(self, entries, total=None):
        """Create standard FHIR Bundle response"""
        if total is None:
            total = len(entries)
        
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": total,
            "entry": entries
        }


class FHIRPatientViewSet(FHIRBaseViewSet):
    """FHIR Patient Resource Endpoint - GET /fhir/r4/Patient"""
    
    def get_queryset(self):
        """Users can only access their own patient resource"""
        return User.objects.filter(id=self.request.user.id)
    
    def retrieve(self, request, pk=None):
        """
        GET /fhir/r4/Patient/{id}
        Retrieve a specific patient by ID (must be current user)
        """
        if str(pk) != str(request.user.id):
            return Response(
                {"error": "You can only access your own patient data"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = request.user
        serializer = FHIRPatientSerializer(user)
        fhir_data = serializer.to_fhir()
        
        logger.info(f"Retrieved FHIR Patient: {user.id}")
        return Response(fhir_data, status=status.HTTP_200_OK)
    
    def list(self, request):
        """
        GET /fhir/r4/Patient
        Returns current user's patient data in a Bundle
        """
        user = request.user
        serializer = FHIRPatientSerializer(user)
        fhir_data = serializer.to_fhir()
        
        logger.info(f"Listed FHIR Patient for user: {user.id}")
        
        return Response(
            self.get_bundle_response([
                {
                    "fullUrl": f"https://meditrack.up.railway.app/fhir/r4/Patient/{user.id}",
                    "resource": fhir_data,
                    "search": {"mode": "match"}
                }
            ]),
            status=status.HTTP_200_OK
        )


class FHIRMedicationViewSet(FHIRBaseViewSet):
    """FHIR Medication Resource - GET /fhir/r4/Medication"""
    
    def list(self, request):
        """
        GET /fhir/r4/Medication
        List all medications for current user
        """
        medications = Medication.objects.filter(user=request.user).order_by('-created_at')
        
        entries = []
        for med in medications:
            serializer = FHIRMedicationSerializer(med)
            med_resource = serializer.to_fhir_medication_resource()
            
            entries.append({
                "fullUrl": f"https://meditrack.up.railway.app/fhir/r4/Medication/{med_resource['id']}",
                "resource": med_resource,
                "search": {"mode": "match"}
            })
        
        logger.info(f"Retrieved {len(medications)} FHIR Medications for user {request.user.id}")
        
        return Response(
            self.get_bundle_response(entries, total=len(entries)),
            status=status.HTTP_200_OK
        )
    
    def retrieve(self, request, pk=None):
        """
        GET /fhir/r4/Medication/{id}
        Retrieve a specific medication by ID
        """
        medication = get_object_or_404(Medication, id=pk, user=request.user)
        serializer = FHIRMedicationSerializer(medication)
        fhir_data = serializer.to_fhir_medication_resource()
        
        logger.info(f"Retrieved FHIR Medication: {pk}")
        return Response(fhir_data, status=status.HTTP_200_OK)


class FHIRMedicationStatementViewSet(FHIRBaseViewSet):
    """FHIR MedicationStatement Resource - GET /fhir/r4/MedicationStatement"""
    
    def list(self, request):
        """
        GET /fhir/r4/MedicationStatement
        List active medications with their statements
        """
        # Get active medications (no end_date or future end_date)
        from django.utils import timezone
        today = timezone.now().date()
        
        medications = Medication.objects.filter(
            user=request.user,
            is_active=True
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        ).order_by('-created_at')
        
        entries = []
        for med in medications:
            serializer = FHIRMedicationSerializer(med)
            stmt_resource = serializer.to_fhir_medication_statement(str(request.user.id))
            
            entries.append({
                "fullUrl": f"https://meditrack.up.railway.app/fhir/r4/MedicationStatement/{stmt_resource['id']}",
                "resource": stmt_resource,
                "search": {"mode": "match"}
            })
        
        logger.info(f"Retrieved {len(medications)} FHIR MedicationStatements for user {request.user.id}")
        
        return Response(
            self.get_bundle_response(entries, total=len(entries)),
            status=status.HTTP_200_OK
        )
    
    def retrieve(self, request, pk=None):
        """
        GET /fhir/r4/MedicationStatement/{id}
        Retrieve a specific medication statement
        """
        medication = get_object_or_404(Medication, id=pk, user=request.user)
        serializer = FHIRMedicationSerializer(medication)
        fhir_data = serializer.to_fhir_medication_statement(str(request.user.id))
        
        logger.info(f"Retrieved FHIR MedicationStatement: {pk}")
        return Response(fhir_data, status=status.HTTP_200_OK)


class FHIRObservationViewSet(FHIRBaseViewSet):
    """FHIR Observation Resource - GET /fhir/r4/Observation"""
    
    def list(self, request):
        """
        GET /fhir/r4/Observation
        List all symptom observations for current user
        Query parameters:
          - category: 'vital-signs' for symptoms, 'mental-health' for moods
        """
        category = request.query_params.get('category', None)
        
        entries = []
        
        # Add symptom observations
        if category is None or category == 'vital-signs':
            symptoms = Symptom.objects.filter(user=request.user).order_by('-date', '-logged_at')
            
            for symptom in symptoms:
                serializer = FHIRObservationSerializer(symptom)
                obs_resource = serializer.to_fhir(str(request.user.id))
                
                entries.append({
                    "fullUrl": f"https://meditrack.up.railway.app/fhir/r4/Observation/{obs_resource['id']}",
                    "resource": obs_resource,
                    "search": {"mode": "match"}
                })
        
        # Add mood observations
        if category is None or category == 'mental-health':
            moods = Moodlog.objects.filter(user=request.user).order_by('-date', '-logged_at')
            
            for mood in moods:
                serializer = FHIRMoodObservationSerializer(mood)
                obs_resource = serializer.to_fhir(str(request.user.id))
                
                entries.append({
                    "fullUrl": f"https://meditrack.up.railway.app/fhir/r4/Observation/{obs_resource['id']}",
                    "resource": obs_resource,
                    "search": {"mode": "match"}
                })
        
        logger.info(f"Retrieved {len(entries)} FHIR Observations for user {request.user.id}")
        
        return Response(
            self.get_bundle_response(entries, total=len(entries)),
            status=status.HTTP_200_OK
        )
    
    def retrieve(self, request, pk=None):
        """
        GET /fhir/r4/Observation/{id}
        Retrieve a specific observation by ID
        Handles both symptom (obs-symptom-*) and mood (obs-mood-*) observations
        """
        # Determine if this is a symptom or mood observation
        if pk.startswith('obs-mood-'):
            mood_id = pk.replace('obs-mood-', '')
            mood = get_object_or_404(Moodlog, id=mood_id, user=request.user)
            serializer = FHIRMoodObservationSerializer(mood)
            fhir_data = serializer.to_fhir(str(request.user.id))
        else:
            # Assume symptom observation
            symptom_id = pk.replace('obs-symptom-', '')
            symptom = get_object_or_404(Symptom, id=symptom_id, user=request.user)
            serializer = FHIRObservationSerializer(symptom)
            fhir_data = serializer.to_fhir(str(request.user.id))
        
        logger.info(f"Retrieved FHIR Observation: {pk}")
        return Response(fhir_data, status=status.HTTP_200_OK)


class FHIRMetadataView(APIView):
    """FHIR CapabilityStatement - GET /fhir/r4/metadata"""
    permission_classes = [] 
    def get(self, request):
        """
        Return FHIR CapabilityStatement describing server capabilities
        This is the standard FHIR metadata endpoint
        """
        return Response({
            "resourceType": "CapabilityStatement",
            "status": "active",
            "date": "2025-01-01",
            "publisher": "MediTrack",
            "kind": "instance",
            "implementation": {
                "description": "MediTrack FHIR API - Patient Health Tracking and Medication Management",
                "url": "https://meditrack.up.railway.app/fhir/r4"
            },
            "fhirVersion": "4.0.1",
            "acceptUnknown": "both",
            "format": ["json", "xml"],
            "rest": [
                {
                    "mode": "server",
                    "security": {
                        "cors": True,
                        "service": [
                            {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                                        "code": "OAuth",
                                        "display": "OAuth"
                                    }
                                ]
                            }
                        ],
                        "description": "Authentication via JWT bearer tokens"
                    },
                    "resource": [
                        {
                            "type": "Patient",
                            "interaction": [
                                {"code": "read", "documentation": "Read individual patient records"},
                                {"code": "search-type", "documentation": "Search for patients"}
                            ]
                        },
                        {
                            "type": "Medication",
                            "interaction": [
                                {"code": "read", "documentation": "Read medication information"},
                                {"code": "search-type", "documentation": "Search for medications"}
                            ]
                        },
                        {
                            "type": "MedicationStatement",
                            "interaction": [
                                {"code": "read", "documentation": "Read medication statements"},
                                {"code": "search-type", "documentation": "Search for medication statements"}
                            ]
                        },
                        {
                            "type": "Observation",
                            "interaction": [
                                {"code": "read", "documentation": "Read observations (symptoms, moods)"},
                                {"code": "search-type", "documentation": "Search for observations"}
                            ]
                        }
                    ]
                }
            ]
        })


class SMARTConfigurationView(APIView):
    """SMART on FHIR Configuration - GET /fhir/r4/.well-known/smart-configuration"""
    permission_classes = []
    def get(self, request):
        """
        Return SMART on FHIR configuration
        Enables third-party healthcare apps to discover OAuth endpoints
        """
        return Response({
            "authorization_endpoint": "https://meditrack.up.railway.app/api/auth/authorize/",
            "token_endpoint": "https://meditrack.up.railway.app/api/auth/token/",
            "introspection_endpoint": "https://meditrack.up.railway.app/api/auth/introspect/",
            "revocation_endpoint": "https://meditrack.up.railway.app/api/auth/logout/",
            "capabilities": [
                "launch-ehr",
                "launch-standalone",
                "client-public",
                "sso-openid-connect",
                "context-passthrough-banner",
                "permission-patient",
                "permission-offline"
            ],
            "response_types_supported": ["code", "id_token"],
            "scopes_supported": [
                "openid",
                "fhirUser",
                "offline_access",
                "patient/Patient.read",
                "patient/Medication.read",
                "patient/MedicationStatement.read",
                "patient/Observation.read"
            ],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic"]
        })
