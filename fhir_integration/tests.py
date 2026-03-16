# fhir_integration/tests.py
"""
Comprehensive test suite for FHIR API endpoints
Tests FHIR resource serialization, API responses, permissions, and data consistency
Run with: python manage.py test fhir_integration --verbosity=2
"""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from medications.models import Medication
from symptoms.models import Symptom, Moodlog
from datetime import datetime, date, timedelta
import json

User = get_user_model()


# ============================================================================
# Phase 1: Basic Setup & Authentication Tests
# ============================================================================

class FHIRAuthenticationTest(APITestCase):
    """Test that FHIR endpoints require authentication"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_metadata_accessible_without_auth(self):
        """Metadata endpoint should be accessible without authentication"""
        response = self.client.get('/fhir/r4/metadata/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'CapabilityStatement')
    
    def test_patient_requires_authentication(self):
        """Patient endpoint should require authentication"""
        response = self.client.get('/fhir/r4/Patient/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_medication_requires_authentication(self):
        """Medication endpoint should require authentication"""
        response = self.client.get('/fhir/r4/Medication/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_observation_requires_authentication(self):
        """Observation endpoint should require authentication"""
        response = self.client.get('/fhir/r4/Observation/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_access_with_valid_token(self):
        """Authenticated user should access FHIR endpoints"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/fhir/r4/Patient/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================================
# Phase 2: Patient Resource Tests
# ============================================================================

class FHIRPatientResourceTest(APITestCase):
    """Test FHIR Patient resource mapping"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='johndoe',
            email='john@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            phone='+1234567890',
            date_of_birth=date(1990, 1, 15)
        )
        self.client.force_authenticate(user=self.user)
    
    def test_fhir_patient_list(self):
        """GET /fhir/r4/Patient - should return user's data in Bundle"""
        response = self.client.get('/fhir/r4/Patient/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Bundle')
        self.assertEqual(response.data['type'], 'searchset')
        self.assertEqual(response.data['total'], 1)
        
        # Check patient resource in bundle
        patient = response.data['entry'][0]['resource']
        self.assertEqual(patient['resourceType'], 'Patient')
        self.assertEqual(patient['id'], str(self.user.id))
    
    def test_fhir_patient_retrieve(self):
        """GET /fhir/r4/Patient/{id} - should return patient resource"""
        response = self.client.get(f'/fhir/r4/Patient/{self.user.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Patient')
        self.assertEqual(response.data['id'], str(self.user.id))
    
    def test_patient_contains_demographics(self):
        """Patient resource should contain required demographic fields"""
        response = self.client.get(f'/fhir/r4/Patient/{self.user.id}/')
        patient = response.data
        
        # Check required fields
        self.assertIn('name', patient)
        self.assertIn('telecom', patient)
        self.assertIn('birthDate', patient)
        self.assertIn('gender', patient)
        
        # Verify values
        self.assertEqual(patient['birthDate'], '1990-01-15')
        
        # Check telecom (should have email and phone)
        emails = [t for t in patient['telecom'] if t['system'] == 'email']
        phones = [t for t in patient['telecom'] if t['system'] == 'phone']
        self.assertEqual(len(emails), 1)
        self.assertEqual(len(phones), 1)
    
    def test_patient_cannot_access_other_user_data(self):
        """User should not be able to access another user's patient resource"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        response = self.client.get(f'/fhir/r4/Patient/{other_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================================
# Phase 3: Medication Resource Tests
# ============================================================================

class FHIRMedicationResourceTest(APITestCase):
    """Test FHIR Medication and MedicationStatement resources"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test medications
        self.med1 = Medication.objects.create(
            user=self.user,
            name='Aspirin',
            dosage='100mg',
            frequency='once_daily',
            start_date=date.today(),
            notes='For headaches'
        )
        
        self.med2 = Medication.objects.create(
            user=self.user,
            name='Lisinopril',
            dosage='10mg',
            frequency='twice_daily',
            start_date=date.today() - timedelta(days=30),
            is_active=True
        )
    
    def test_medication_list(self):
        """GET /fhir/r4/Medication - should list all medications"""
        response = self.client.get('/fhir/r4/Medication/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Bundle')
        self.assertEqual(response.data['total'], 2)
        
        # Verify medications in bundle
        med_names = [entry['resource']['code']['text'] for entry in response.data['entry']]
        self.assertIn('Aspirin', med_names)
        self.assertIn('Lisinopril', med_names)
    
    def test_medication_retrieve(self):
        """GET /fhir/r4/Medication/{id} - should return medication resource"""
        response = self.client.get(f'/fhir/r4/Medication/{self.med1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Medication')
        self.assertEqual(response.data['code']['text'], 'Aspirin')
    
    def test_medication_statement_list(self):
        """GET /fhir/r4/MedicationStatement - should list active medications"""
        response = self.client.get('/fhir/r4/MedicationStatement/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Bundle')
        # Should only include active medications
        self.assertGreaterEqual(response.data['total'], 1)
    
    def test_medication_statement_contains_dosage(self):
        """MedicationStatement should contain dosage information"""
        response = self.client.get(f'/fhir/r4/MedicationStatement/{self.med1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stmt = response.data
        
        # Check structure
        self.assertIn('dosage', stmt)
        self.assertEqual(len(stmt['dosage']), 1)
        dosage = stmt['dosage'][0]
        self.assertIn('text', dosage)
        self.assertIn('timing', dosage)
    
    def test_medication_not_visible_to_other_user(self):
        """Medications should only be visible to their owner"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Other user should see empty list
        self.client.force_authenticate(user=other_user)
        response = self.client.get('/fhir/r4/Medication/')
        self.assertEqual(response.data['total'], 0)


# ============================================================================
# Phase 4: Observation (Symptom) Resource Tests
# ============================================================================

class FHIRSymptomObservationTest(APITestCase):
    """Test FHIR Observation resource for symptoms"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test symptoms
        self.symptom1 = Symptom.objects.create(
            user=self.user,
            name='Headache',
            severity=7,
            date=date.today(),
            notes='Mild headache'
        )
        
        self.symptom2 = Symptom.objects.create(
            user=self.user,
            name='Nausea',
            severity=5,
            date=date.today() - timedelta(days=1),
            notes='Nausea in morning'
        )
    
    def test_observation_list(self):
        """GET /fhir/r4/Observation - should list all observations"""
        response = self.client.get('/fhir/r4/Observation/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Bundle')
        self.assertEqual(response.data['total'], 2)
    
    def test_observation_retrieve(self):
        """GET /fhir/r4/Observation/{id} - should return observation"""
        response = self.client.get(f'/fhir/r4/Observation/obs-symptom-{self.symptom1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Observation')
        self.assertEqual(response.data['code']['text'], 'Headache')
    
    def test_observation_contains_severity(self):
        """Observation should contain severity value"""
        response = self.client.get(f'/fhir/r4/Observation/obs-symptom-{self.symptom1.id}/')
        obs = response.data
        
        # Check value
        self.assertIn('valueQuantity', obs)
        self.assertEqual(obs['valueQuantity']['value'], 7)
        self.assertIn('note', obs)
    
    def test_observation_snomed_codes(self):
        """Observation should map symptoms to SNOMED CT codes"""
        response = self.client.get(f'/fhir/r4/Observation/obs-symptom-{self.symptom1.id}/')
        obs = response.data
        
        # Check SNOMED code for headache
        self.assertEqual(obs['code']['coding'][0]['system'], 'http://snomed.info/sct')
        self.assertEqual(obs['code']['coding'][0]['code'], '25064002')  # Headache code


class FHIRMoodObservationTest(APITestCase):
    """Test FHIR Observation resource for mood logs"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test mood logs
        self.mood1 = Moodlog.objects.create(
            user=self.user,
            mood=5,  # Very Good
            date=date.today(),
            notes='Feeling great'
        )
    
    def test_mood_observation_in_list(self):
        """Mood logs should appear in observation list"""
        response = self.client.get('/fhir/r4/Observation/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include mood observation
        mood_obs = [e for e in response.data['entry'] if 'obs-mood' in e['resource']['id']]
        self.assertEqual(len(mood_obs), 1)
    
    def test_mood_observation_retrieve(self):
        """GET mood observation should return mood-specific observation"""
        response = self.client.get(f'/fhir/r4/Observation/obs-mood-{self.mood1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        obs = response.data
        self.assertEqual(obs['resourceType'], 'Observation')
        self.assertIn('mental-health', obs['category'][0]['coding'][0]['code'])


# ============================================================================
# Phase 5: Data Consistency Tests
# ============================================================================

class FHIRDataConsistencyTest(APITestCase):
    """Verify FHIR data matches original MediTrack data"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone='+1234567890'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_patient_fhir_consistency(self):
        """Patient data should be consistent between API and FHIR"""
        # Get via FHIR
        response = self.client.get(f'/fhir/r4/Patient/{self.user.id}/')
        fhir_patient = response.data
        
        # Verify data matches
        self.assertEqual(fhir_patient['id'], str(self.user.id))
        self.assertIn(self.user.email, [t['value'] for t in fhir_patient['telecom']])
    
    def test_medication_fhir_consistency(self):
        """Medication FHIR conversion should preserve data"""
        med = Medication.objects.create(
            user=self.user,
            name='Aspirin',
            dosage='100mg',
            frequency='once_daily',
            start_date=date.today(),
            notes='For pain'
        )
        
        response = self.client.get(f'/fhir/r4/Medication/{med.id}/')
        fhir_med = response.data
        
        # Verify all fields preserved
        self.assertEqual(fhir_med['code']['text'], 'Aspirin')
        self.assertEqual(fhir_med['id'], f'med-{med.id}')
    
    def test_symptom_fhir_consistency(self):
        """Symptom FHIR conversion should preserve severity"""
        symptom = Symptom.objects.create(
            user=self.user,
            name='Headache',
            severity=8,
            date=date.today(),
            notes='Severe headache'
        )
        
        response = self.client.get(f'/fhir/r4/Observation/obs-symptom-{symptom.id}/')
        fhir_obs = response.data
        
        # Verify severity preserved
        self.assertEqual(fhir_obs['valueQuantity']['value'], 8)
        self.assertEqual(fhir_obs['code']['text'], 'Headache')


# ============================================================================
# Phase 6: Bundle & Pagination Tests
# ============================================================================

class FHIRBundleFormatTest(APITestCase):
    """Test FHIR Bundle responses are correctly formatted"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create multiple resources
        for i in range(5):
            Medication.objects.create(
                user=self.user,
                name=f'Med{i}',
                dosage='100mg',
                frequency='once_daily',
                start_date=date.today()
            )
    
    def test_bundle_has_required_fields(self):
        """Bundle should have required FHIR fields"""
        response = self.client.get('/fhir/r4/Medication/')
        bundle = response.data
        
        self.assertEqual(bundle['resourceType'], 'Bundle')
        self.assertEqual(bundle['type'], 'searchset')
        self.assertIn('total', bundle)
        self.assertIn('entry', bundle)
    
    def test_bundle_entries_have_structure(self):
        """Bundle entries should have fullUrl, resource, search"""
        response = self.client.get('/fhir/r4/Medication/')
        
        for entry in response.data['entry']:
            self.assertIn('fullUrl', entry)
            self.assertIn('resource', entry)
            self.assertIn('search', entry)
            self.assertEqual(entry['search']['mode'], 'match')


# ============================================================================
# Phase 7: SMART Configuration Test
# ============================================================================

class SMARTConfigurationTest(APITestCase):
    """Test SMART on FHIR configuration endpoint"""
    
    def test_smart_config_available(self):
        """SMART configuration should be publicly available"""
        response = self.client.get('/fhir/r4/.well-known/smart-configuration')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('authorization_endpoint', response.data)
        self.assertIn('token_endpoint', response.data)
        self.assertIn('scopes_supported', response.data)
