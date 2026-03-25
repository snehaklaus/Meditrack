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
from django.core.mail import send_mail
from django.utils import timezone
import time
import secrets
from .serializers import (
    UserRegistrationSerializer, 
    UserSerializer, 
    PatientSerializer, 
    DoctorPatientsSerializer
)
from .models import User, PasswordResetToken
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


# ⭐ Forgot Password - accepts email, sends reset link
@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='dispatch')
class ForgotPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()

        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Always return the same response to prevent email enumeration
        success_response = Response(
            {'message': 'If an account with that email exists, a password reset link has been sent.'},
            status=status.HTTP_200_OK
        )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            # Don't reveal that the email doesn't exist
            return success_response

        # Invalidate any existing unused tokens for this user
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        # Create a new reset token
        reset_token = PasswordResetToken.objects.create(user=user)

        # Build reset URL — points to the frontend
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://meditrack7.vercel.app')
        reset_url = f"{frontend_url}?reset_token={reset_token.token}"

        # Send email using existing Gmail SMTP config
        try:
            send_mail(
                subject='Reset Your MediTrack Password',
                message=(
                    f"Hi {user.username},\n\n"
                    f"You requested a password reset for your MediTrack account.\n\n"
                    f"Click the link below to set a new password. This link expires in 1 hour.\n\n"
                    f"{reset_url}\n\n"
                    f"If you did not request this, you can safely ignore this email.\n\n"
                    f"— The MediTrack Team"
                ),
                html_message=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #2563eb, #0891b2); padding: 24px; border-radius: 12px 12px 0 0; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 24px;">🔒 MediTrack</h1>
                        <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 14px;">Password Reset Request</p>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-top: none; padding: 32px; border-radius: 0 0 12px 12px;">
                        <p style="color: #334155; font-size: 16px;">Hi <strong>{user.username}</strong>,</p>
                        <p style="color: #64748b; font-size: 15px; line-height: 1.6;">
                            We received a request to reset your MediTrack password.
                            Click the button below to choose a new password. This link expires in <strong>1 hour</strong>.
                        </p>
                        <div style="text-align: center; margin: 32px 0;">
                            <a href="{reset_url}"
                               style="background: linear-gradient(135deg, #2563eb, #0891b2); color: white;
                                      padding: 14px 32px; border-radius: 8px; text-decoration: none;
                                      font-weight: 600; font-size: 16px; display: inline-block;">
                                Reset My Password →
                            </a>
                        </div>
                        <p style="color: #94a3b8; font-size: 13px; margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 16px;">
                            If you didn't request this, you can safely ignore this email.
                            Your password will not change unless you click the link above.
                        </p>
                    </div>
                </div>
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"❌ Failed to send password reset email: {str(e)}")
            # Still return success to avoid email enumeration, but log the error
            return success_response

        return success_response


# ⭐ Reset Password - validates token and sets new password
class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_str = request.data.get('token', '').strip()
        new_password = request.data.get('password', '')
        confirm_password = request.data.get('confirm_password', '')

        # Validate inputs
        if not token_str:
            return Response({'error': 'Reset token is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not new_password:
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)

        # Look up token
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(token=token_str)
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid or expired reset link. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check validity
        if not reset_token.is_valid:
            return Response(
                {'error': 'This reset link has expired or already been used. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user = reset_token.user
        user.set_password(new_password)
        user.save()

        # Mark token as used
        reset_token.used = True
        reset_token.save()

        # Invalidate any other pending tokens for this user
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        return Response(
            {'message': 'Password reset successfully. You can now log in with your new password.'},
            status=status.HTTP_200_OK
        )