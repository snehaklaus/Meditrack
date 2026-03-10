from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.db import IntegrityError
import time
from .serializers import (
    UserRegistrationSerializer, 
    UserSerializer, 
    PatientSerializer, 
    DoctorPatientsSerializer
)
from .models import User
from .permissions import IsDoctor, IsPatient


# ⭐ Registration endpoint - allows anyone
@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response(
                {
                    'success': True,
                    'message': 'User registered successfully',
                    'user': response.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


# ⭐ Login endpoint - allows anyone, returns JWT tokens
@method_decorator(ratelimit(key='ip', rate='10/h', method='POST'), name='dispatch')
class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return Response(
                {
                    'success': True,
                    'message': 'Login successful',
                    'data': response.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': 'Invalid credentials'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )


# Profile endpoint - requires authentication
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# Doctor can see their assigned patients
class PatientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DoctorPatientsSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return self.request.user.assigned_patients.all()


# Patient can assign a doctor to themselves
class AssignDoctorView(generics.UpdateAPIView):
    serializer_class = PatientSerializer
    permission_classes = [IsPatient]

    def get_object(self):
        return self.request.user
    

# Doctor can view detailed information about a specific assigned patient
class PatientDetailView(generics.RetrieveAPIView):
    permission_classes=[IsDoctor]
    serializer_class=PatientSerializer

    def get_queryset(self):
        return self.request.user.assigned_patients.all()
    
    def retrieve(self, request, *args, **kwargs):
        patient=self.get_object()

        from medications.serializers import MedicationSerializer
        from symptoms.serializers import DoctorSymptomSerializer,DoctorMoodlogSerializer
        patient_data=self.get_serializer(patient).data

        medications=patient.medications.filter(is_active=True)
        symptoms=patient.symptoms.all()[:20]
        moods=patient.moods.all()[:30]

        response_data={
            'patient':patient_data,
            'medications': MedicationSerializer(medications,many=True).data,
            'recent_symptoms':DoctorSymptomSerializer(symptoms,many=True).data,
            'mood_logs':DoctorMoodlogSerializer(moods,many=True).data,
        }
        return Response(response_data,status=status.HTTP_200_OK)


# Google OAuth Login with clock skew tolerance
class GoogleAuthView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        
        if not token:
            return Response({'error': 'Token required'}, status=400)

        try:
            # Verify token with Google with clock skew tolerance
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID,
                clock_skew_in_seconds=10  # Allow 10 seconds clock skew
            )

            email = idinfo.get('email')
            name = idinfo.get('name', '')
            google_id = idinfo.get('sub')

            if not email:
                return Response({'error': 'Email not provided by Google'}, status=400)

            # Check if user exists by email
            user = User.objects.filter(email=email).first()

            if user:
                # Existing user — just log them in
                refresh = RefreshToken.for_user(user)
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'is_new_user': False,
                }, status=200)
            else:
                # New user — return Google data
                return Response({
                    'is_new_user': True,
                    'email': email,
                    'name': name,
                    'google_id': google_id,
                }, status=200)

        except ValueError as e:
            print(f"❌ Token verification error: {str(e)}")
            return Response({'error': f'Invalid token: {str(e)}'}, status=400)
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return Response({'error': 'Authentication failed'}, status=500)


# Complete Google OAuth Registration
class GoogleRegisterCompleteView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        username = request.data.get('username')
        google_id = request.data.get('google_id')
        role = request.data.get('role', 'patient')
        name = request.data.get('name', '')

        # Validation
        if not all([email, username, google_id]):
            return Response({'error': 'Missing required fields'}, status=400)

        # Check username uniqueness
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already taken'}, status=400)

        # Check email uniqueness
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already registered'}, status=400)

        try:
            # Split name into first/last
            name_parts = name.split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            # Create user without password (OAuth user)
            user = User.objects.create(
                username=username,
                email=email,
                role=role,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()
            user.save()

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'is_new_user': False,
            }, status=201)

        except IntegrityError as e:
            return Response({'error': 'User creation failed. Please try again.'}, status=400)
        except Exception as e:
            return Response({'error': f'Registration failed: {str(e)}'}, status=500)