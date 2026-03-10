"""
MediTrack Backend - Unit Tests for Accounts App
Tests: User model, serializers, registration, login, profile, doctor/patient flows
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta

User = get_user_model()


# ─────────────────────────────────────────────
# 1. USER MODEL TESTS
# ─────────────────────────────────────────────

class UserModelTest(TestCase):
    """Tests for the custom User model"""

    def setUp(self):
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@test.com',
            password='SecurePass123',
            role='patient'
        )
        self.doctor = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='SecurePass123',
            role='doctor'
        )

    def test_user_created_with_correct_role(self):
        self.assertEqual(self.patient.role, 'patient')
        self.assertEqual(self.doctor.role, 'doctor')

    def test_default_role_is_patient(self):
        user = User.objects.create_user(
            username='defaultuser',
            email='default@test.com',
            password='SecurePass123'
        )
        self.assertEqual(user.role, 'patient')

    def test_user_str_representation(self):
        self.assertEqual(str(self.patient), 'testpatient (patient)')
        self.assertEqual(str(self.doctor), 'testdoctor (doctor)')

    def test_email_is_unique(self):
        # Django raises ValidationError via serializer before hitting DB
        from accounts.serializers import UserRegistrationSerializer
        serializer = UserRegistrationSerializer(data={
            'username': 'anotheruser',
            'email': 'patient@test.com',  # duplicate email
            'password': 'SecurePass123',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_email_digest_enabled_by_default(self):
        self.assertTrue(self.patient.email_digest_enabled)

    def test_assign_doctor_to_patient(self):
        self.patient.assigned_doctor = self.doctor
        self.patient.save()
        self.assertEqual(self.patient.assigned_doctor, self.doctor)

    def test_doctor_can_have_multiple_patients(self):
        patient2 = User.objects.create_user(
            username='patient2',
            email='patient2@test.com',
            password='SecurePass123',
            role='patient'
        )
        self.patient.assigned_doctor = self.doctor
        self.patient.save()
        patient2.assigned_doctor = self.doctor
        patient2.save()

        assigned = self.doctor.assigned_patients.all()
        self.assertIn(self.patient, assigned)
        self.assertIn(patient2, assigned)

    def test_user_date_of_birth_field(self):
        self.patient.date_of_birth = date(1995, 6, 15)
        self.patient.save()
        refreshed = User.objects.get(pk=self.patient.pk)
        self.assertEqual(refreshed.date_of_birth, date(1995, 6, 15))

    def test_phone_field_can_be_blank(self):
        user = User.objects.create_user(
            username='nophone',
            email='nophone@test.com',
            password='SecurePass123'
        )
        self.assertEqual(user.phone, '')


# ─────────────────────────────────────────────
# 2. SERIALIZER TESTS
# ─────────────────────────────────────────────

class UserRegistrationSerializerTest(TestCase):
    """Tests for UserRegistrationSerializer validation logic"""

    def _get_serializer(self, data):
        from accounts.serializers import UserRegistrationSerializer
        return UserRegistrationSerializer(data=data)

    def test_valid_registration_data(self):
        serializer = self._get_serializer({
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'SecurePass123',
            'role': 'patient'
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_password_too_short_is_invalid(self):
        serializer = self._get_serializer({
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'short',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_duplicate_username_is_invalid(self):
        User.objects.create_user(
            username='taken', email='taken@test.com', password='SecurePass123'
        )
        serializer = self._get_serializer({
            'username': 'taken',
            'email': 'new@test.com',
            'password': 'SecurePass123',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_duplicate_email_is_invalid(self):
        User.objects.create_user(
            username='existing', email='taken@test.com', password='SecurePass123'
        )
        serializer = self._get_serializer({
            'username': 'newuser',
            'email': 'taken@test.com',
            'password': 'SecurePass123',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_missing_email_is_invalid(self):
        serializer = self._get_serializer({
            'username': 'newuser',
            'password': 'SecurePass123',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class UserSerializerTest(TestCase):
    """Tests for UserSerializer update validation"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='SecurePass123'
        )

    def _get_serializer(self, data, instance=None):
        from accounts.serializers import UserSerializer
        return UserSerializer(instance=instance, data=data, partial=True)

    def test_valid_phone_number(self):
        serializer = self._get_serializer(
            {'phone': '+447911123456'}, instance=self.user
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_phone_number(self):
        serializer = self._get_serializer(
            {'phone': 'not-a-phone'}, instance=self.user
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)

    def test_future_date_of_birth_is_invalid(self):
        future_date = date.today() + timedelta(days=1)
        serializer = self._get_serializer(
            {'date_of_birth': future_date.isoformat()}, instance=self.user
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('date_of_birth', serializer.errors)

    def test_valid_date_of_birth(self):
        serializer = self._get_serializer(
            {'date_of_birth': '1995-06-15'}, instance=self.user
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_role_is_read_only(self):
        serializer = self._get_serializer(
            {'role': 'doctor'}, instance=self.user
        )
        serializer.is_valid()
        # role should not appear in validated_data since it's read_only
        self.assertNotIn('role', serializer.validated_data)


# ─────────────────────────────────────────────
# 3. REGISTRATION API TESTS
# ─────────────────────────────────────────────

class RegisterViewTest(APITestCase):
    """Tests for POST /api/auth/register/"""

    def setUp(self):
        self.url = reverse('register')

    @override_settings(RATELIMIT_ENABLE=False)
    def test_successful_registration(self):
        data = {
            'username': 'newpatient',
            'email': 'newpatient@test.com',
            'password': 'SecurePass123',
            'role': 'patient'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertTrue(User.objects.filter(username='newpatient').exists())

    @override_settings(RATELIMIT_ENABLE=False)
    def test_registration_creates_patient_by_default(self):
        data = {
            'username': 'defaultpatient',
            'email': 'dp@test.com',
            'password': 'SecurePass123',
        }
        self.client.post(self.url, data)
        user = User.objects.get(username='defaultpatient')
        self.assertEqual(user.role, 'patient')

    @override_settings(RATELIMIT_ENABLE=False)
    def test_registration_with_doctor_role(self):
        data = {
            'username': 'newdoctor',
            'email': 'newdoctor@test.com',
            'password': 'SecurePass123',
            'role': 'doctor'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newdoctor')
        self.assertEqual(user.role, 'doctor')

    @override_settings(RATELIMIT_ENABLE=False)
    def test_registration_with_duplicate_username_fails(self):
        User.objects.create_user(
            username='taken', email='taken@test.com', password='SecurePass123'
        )
        data = {
            'username': 'taken',
            'email': 'new@test.com',
            'password': 'SecurePass123',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(RATELIMIT_ENABLE=False)
    def test_registration_with_weak_password_fails(self):
        data = {
            'username': 'weakuser',
            'email': 'weak@test.com',
            'password': '123',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(RATELIMIT_ENABLE=False)
    def test_registration_missing_email_fails(self):
        data = {
            'username': 'noemail',
            'password': 'SecurePass123',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
# 4. LOGIN API TESTS
# ─────────────────────────────────────────────

class LoginViewTest(APITestCase):
    """Tests for POST /api/auth/login/"""

    def setUp(self):
        self.url = reverse('login')
        self.user = User.objects.create_user(
            username='loginuser',
            email='login@test.com',
            password='SecurePass123'
        )

    def test_successful_login_returns_tokens(self):
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'SecurePass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])

    def test_login_with_nonexistent_user_fails(self):
        response = self.client.post(self.url, {
            'username': 'nobody',
            'password': 'SecurePass123'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_empty_credentials_fails(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────
# 5. PROFILE API TESTS
# ─────────────────────────────────────────────

class ProfileViewTest(APITestCase):
    """Tests for GET/PATCH /api/auth/profile/"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@test.com',
            password='SecurePass123',
            role='patient'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('profile')

    def test_get_profile_returns_correct_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'profileuser')
        self.assertEqual(response.data['email'], 'profile@test.com')

    def test_profile_does_not_expose_password(self):
        response = self.client.get(self.url)
        self.assertNotIn('password', response.data)

    def test_update_profile_username(self):
        response = self.client.patch(self.url, {'username': 'updatedname'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile_phone(self):
        response = self.client.patch(self.url, {'phone': '+447911123456'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile_email_digest(self):
        response = self.client.patch(self.url, {'email_digest_enabled': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_cannot_access_profile(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_cannot_be_updated_via_profile(self):
        self.client.patch(self.url, {'role': 'doctor'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'patient')


# ─────────────────────────────────────────────
# 6. DOCTOR / PATIENT FLOW TESTS
# ─────────────────────────────────────────────

class DoctorPatientFlowTest(APITestCase):
    """Tests for doctor-patient assignment and access control"""

    def setUp(self):
        self.doctor = User.objects.create_user(
            username='dr_smith',
            email='dr@test.com',
            password='SecurePass123',
            role='doctor'
        )
        self.patient = User.objects.create_user(
            username='patient_joe',
            email='joe@test.com',
            password='SecurePass123',
            role='patient'
        )

    def test_patient_can_assign_doctor(self):
        self.client.force_authenticate(user=self.patient)
        url = reverse('assign_doctor')
        response = self.client.patch(url, {'assigned_doctor': self.doctor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_doctor_can_view_assigned_patients(self):
        self.patient.assigned_doctor = self.doctor
        self.patient.save()
        self.client.force_authenticate(user=self.doctor)
        url = reverse('patients-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [p['username'] for p in response.data]
        self.assertIn('patient_joe', usernames)

    def test_patient_cannot_access_patients_list(self):
        self.client.force_authenticate(user=self.patient)
        url = reverse('patients-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_cannot_assign_doctor_to_themselves(self):
        self.client.force_authenticate(user=self.doctor)
        url = reverse('assign_doctor')
        response = self.client.patch(url, {'assigned_doctor': self.doctor.id})
        # Doctors don't have patient permission
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_can_view_patient_detail(self):
        self.patient.assigned_doctor = self.doctor
        self.patient.save()
        self.client.force_authenticate(user=self.doctor)
        url = reverse('patient-detail', kwargs={'pk': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['patient']['username'], 'patient_joe')

    def test_doctor_cannot_view_unassigned_patient(self):
        # Patient not assigned to this doctor
        other_doctor = User.objects.create_user(
            username='dr_other',
            email='other@test.com',
            password='SecurePass123',
            role='doctor'
        )
        self.client.force_authenticate(user=other_doctor)
        url = reverse('patient-detail', kwargs={'pk': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)