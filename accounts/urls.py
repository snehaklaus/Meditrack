from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, 
    ProfileView, 
    PatientViewSet, 
    AssignDoctorView, 
    LoginView,
    GoogleAuthView,
    GoogleRegisterCompleteView,
    PatientDetailView,
    ForgotPasswordView,
    ResetPasswordView,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patients')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('assign-doctor/', AssignDoctorView.as_view(), name='assign_doctor'),
    path('google/', GoogleAuthView.as_view(), name='google-auth'), 
    path('google/complete/', GoogleRegisterCompleteView.as_view(), name='google-complete'),  
    path('patients/<int:pk>/', PatientDetailView.as_view(), name='patient-detail'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
] + router.urls