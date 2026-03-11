from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from .models import Medication, MedicationReminder
from .serializers import MedicationSerializer

User = get_user_model()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_patient(username="patient1", password="testpass123"):
    user = User.objects.create_user(
        username=username, password=password, email=f"{username}@test.com"
    )
    user.role = "patient"
    user.save()
    return user


def make_doctor(username="doctor1", password="testpass123"):
    user = User.objects.create_user(
        username=username, password=password, email=f"{username}@test.com"
    )
    user.role = "doctor"
    user.save()
    return user


def make_medication(user, **kwargs):
    defaults = dict(
        name="Aspirin",
        dosage="100mg",
        frequency="once_daily",
        start_date=date.today(),
        is_active=True,
    )
    defaults.update(kwargs)
    return Medication.objects.create(user=user, **defaults)


# ─────────────────────────────────────────────
# Model Tests
# ─────────────────────────────────────────────

class MedicationModelTest(TestCase):
    def setUp(self):
        self.patient = make_patient()

    def test_str_representation(self):
        med = make_medication(self.patient)
        self.assertIn("Aspirin", str(med))
        self.assertIn("100mg", str(med))
        self.assertIn(self.patient.username, str(med))

    def test_default_is_active(self):
        med = make_medication(self.patient)
        self.assertTrue(med.is_active)

    def test_ordering_newest_first(self):
        med1 = make_medication(self.patient, name="Med A")
        med2 = make_medication(self.patient, name="Med B")
        meds = list(Medication.objects.filter(user=self.patient))
        self.assertEqual(meds[0], med2)  # newest first

    def test_custom_schedule_nullable(self):
        med = make_medication(self.patient, frequency="once_daily", custom_schedule=None)
        self.assertIsNone(med.custom_schedule)

    def test_custom_schedule_json(self):
        schedule = ["08:00", "14:00", "20:00"]
        med = make_medication(
            self.patient, frequency="custom", custom_schedule=schedule
        )
        self.assertEqual(med.custom_schedule, schedule)

    def test_end_date_nullable(self):
        med = make_medication(self.patient, end_date=None)
        self.assertIsNone(med.end_date)

    def test_frequency_choices(self):
        valid_choices = [c[0] for c in Medication.FREQUENCY_CHOICES]
        for choice in valid_choices:
            med = make_medication(self.patient, frequency=choice)
            self.assertEqual(med.frequency, choice)

    def test_notes_optional(self):
        med = make_medication(self.patient, notes="")
        self.assertEqual(med.notes, "")

    def test_timestamps_set_on_create(self):
        med = make_medication(self.patient)
        self.assertIsNotNone(med.created_at)
        self.assertIsNotNone(med.updated_at)


class MedicationReminderModelTest(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.med = make_medication(self.patient)

    def test_str_representation(self):
        reminder = MedicationReminder.objects.create(
            medication=self.med,
            scheduled_time="08:00:00",
        )
        self.assertIn(self.med.name, str(reminder))
        self.assertIn("08:00:00", str(reminder))

    def test_default_was_taken_false(self):
        reminder = MedicationReminder.objects.create(
            medication=self.med, scheduled_time="09:00:00"
        )
        self.assertFalse(reminder.was_taken)

    def test_taken_at_nullable(self):
        reminder = MedicationReminder.objects.create(
            medication=self.med, scheduled_time="09:00:00"
        )
        self.assertIsNone(reminder.taken_at)

    def test_cascade_delete_with_medication(self):
        MedicationReminder.objects.create(
            medication=self.med, scheduled_time="09:00:00"
        )
        self.med.delete()
        self.assertEqual(MedicationReminder.objects.count(), 0)


# ─────────────────────────────────────────────
# Serializer Tests
# ─────────────────────────────────────────────

class MedicationSerializerTest(TestCase):
    def setUp(self):
        self.patient = make_patient()

    def _context(self):
        request = MagicMock()
        request.user = self.patient
        return {"request": request}

    def test_valid_data_creates_medication(self):
        data = {
            "name": "Ibuprofen",
            "dosage": "200mg",
            "frequency": "twice_daily",
            "start_date": str(date.today()),
        }
        serializer = MedicationSerializer(data=data, context=self._context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_end_date_before_start_date_invalid(self):
        data = {
            "name": "Ibuprofen",
            "dosage": "200mg",
            "frequency": "once_daily",
            "start_date": str(date.today()),
            "end_date": str(date.today() - timedelta(days=1)),
        }
        serializer = MedicationSerializer(data=data, context=self._context())
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_custom_frequency_without_schedule_invalid(self):
        data = {
            "name": "Med",
            "dosage": "10mg",
            "frequency": "custom",
            "start_date": str(date.today()),
        }
        serializer = MedicationSerializer(data=data, context=self._context())
        self.assertFalse(serializer.is_valid())

    def test_custom_frequency_with_schedule_valid(self):
        data = {
            "name": "Med",
            "dosage": "10mg",
            "frequency": "custom",
            "start_date": str(date.today()),
            "custom_schedule": ["08:00", "20:00"],
        }
        serializer = MedicationSerializer(data=data, context=self._context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_is_current_true_for_active_today(self):
        med = make_medication(self.patient, start_date=date.today(), end_date=None)
        serializer = MedicationSerializer(med, context=self._context())
        self.assertTrue(serializer.data["is_current"])

    def test_is_current_false_when_ended(self):
        med = make_medication(
            self.patient,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1),
        )
        serializer = MedicationSerializer(med, context=self._context())
        self.assertFalse(serializer.data["is_current"])

    def test_is_current_false_for_future_start(self):
        med = make_medication(
            self.patient, start_date=date.today() + timedelta(days=5)
        )
        serializer = MedicationSerializer(med, context=self._context())
        self.assertFalse(serializer.data["is_current"])

    def test_user_hidden_field_not_in_output(self):
        med = make_medication(self.patient)
        serializer = MedicationSerializer(med, context=self._context())
        # user is a HiddenField — it should NOT appear in serializer.data
        self.assertNotIn("user", serializer.data)

    def test_html_injection_rejected(self):
        data = {
            "name": "<script>alert(1)</script>",
            "dosage": "10mg",
            "frequency": "once_daily",
            "start_date": str(date.today()),
        }
        serializer = MedicationSerializer(data=data, context=self._context())
        self.assertFalse(serializer.is_valid())


# ─────────────────────────────────────────────
# View / API Tests
# ─────────────────────────────────────────────

class MedicationViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = make_patient()
        self.other_patient = make_patient(username="patient2")
        self.doctor = make_doctor()

        # Link doctor → patient
        self.doctor.assigned_patients.add(self.patient)

        self.med = make_medication(self.patient)
        self.list_url = "/api/medications/"

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Authentication ---

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Patient: CRUD ---

    def test_patient_can_list_own_medications(self):
        self._auth(self.patient)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_patient_cannot_see_other_patient_medications(self):
        make_medication(self.other_patient, name="Other Med")
        self._auth(self.patient)
        response = self.client.get(self.list_url)
        names = [m["name"] for m in response.data["results"]]
        self.assertNotIn("Other Med", names)

    def test_patient_can_create_medication(self):
        self._auth(self.patient)
        payload = {
            "name": "Paracetamol",
            "dosage": "500mg",
            "frequency": "twice_daily",
            "start_date": str(date.today()),
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Medication.objects.filter(user=self.patient).count(), 2)

    def test_patient_can_update_own_medication(self):
        self._auth(self.patient)
        url = f"{self.list_url}{self.med.id}/"
        response = self.client.patch(url, {"dosage": "200mg"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.med.refresh_from_db()
        self.assertEqual(self.med.dosage, "200mg")

    def test_patient_can_delete_own_medication(self):
        self._auth(self.patient)
        url = f"{self.list_url}{self.med.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Medication.objects.count(), 0)

    def test_patient_cannot_access_other_medication(self):
        other_med = make_medication(self.other_patient, name="Hidden")
        self._auth(self.patient)
        url = f"{self.list_url}{other_med.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Doctor access ---

    def test_doctor_can_view_assigned_patient_medications(self):
        self._auth(self.doctor)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_doctor_cannot_see_unassigned_patient_medications(self):
        make_medication(self.other_patient, name="Unassigned Med")
        self._auth(self.doctor)
        response = self.client.get(self.list_url)
        names = [m["name"] for m in response.data["results"]]
        self.assertNotIn("Unassigned Med", names)

    # --- Filtering & Search ---

    def test_filter_by_is_active(self):
        make_medication(self.patient, name="Inactive Med", is_active=False)
        self._auth(self.patient)
        response = self.client.get(self.list_url + "?is_active=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for med in response.data["results"]:
            self.assertTrue(med["is_active"])

    def test_filter_by_frequency(self):
        make_medication(self.patient, name="Twice Med", frequency="twice_daily")
        self._auth(self.patient)
        response = self.client.get(self.list_url + "?frequency=twice_daily")
        for med in response.data["results"]:
            self.assertEqual(med["frequency"], "twice_daily")

    def test_search_by_name(self):
        make_medication(self.patient, name="Metformin")
        self._auth(self.patient)
        response = self.client.get(self.list_url + "?search=Metformin")
        names = [m["name"] for m in response.data["results"]]
        self.assertIn("Metformin", names)

    # --- Custom Actions ---

    def test_current_action_returns_active_medications(self):
        # Active and started
        make_medication(
            self.patient, name="Current", is_active=True, start_date=date.today()
        )
        # Inactive
        make_medication(
            self.patient, name="Inactive", is_active=False, start_date=date.today()
        )
        # Future
        make_medication(
            self.patient,
            name="Future",
            is_active=True,
            start_date=date.today() + timedelta(days=5),
        )
        self._auth(self.patient)
        response = self.client.get(self.list_url + "current/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [m["name"] for m in response.data]
        self.assertIn("Current", names)
        self.assertNotIn("Inactive", names)
        self.assertNotIn("Future", names)

    def test_current_excludes_expired(self):
        make_medication(
            self.patient,
            name="Expired",
            is_active=True,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1),
        )
        self._auth(self.patient)
        response = self.client.get(self.list_url + "current/")
        names = [m["name"] for m in response.data]
        self.assertNotIn("Expired", names)

    def test_upcoming_action_returns_future_medications(self):
        make_medication(
            self.patient,
            name="Future Med",
            start_date=date.today() + timedelta(days=3),
        )
        self._auth(self.patient)
        response = self.client.get(self.list_url + "upcoming/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [m["name"] for m in response.data]
        self.assertIn("Future Med", names)

    def test_upcoming_excludes_today_and_past(self):
        self._auth(self.patient)
        response = self.client.get(self.list_url + "upcoming/")
        names = [m["name"] for m in response.data]
        self.assertNotIn("Aspirin", names)  # self.med starts today

    # --- Validation ---

    def test_create_invalid_end_before_start(self):
        self._auth(self.patient)
        payload = {
            "name": "Bad Med",
            "dosage": "10mg",
            "frequency": "once_daily",
            "start_date": str(date.today()),
            "end_date": str(date.today() - timedelta(days=5)),
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_custom_frequency_without_schedule_invalid(self):
        self._auth(self.patient)
        payload = {
            "name": "Custom Med",
            "dosage": "10mg",
            "frequency": "custom",
            "start_date": str(date.today()),
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_custom_frequency_with_schedule_valid(self):
        self._auth(self.patient)
        payload = {
            "name": "Custom Med",
            "dosage": "10mg",
            "frequency": "custom",
            "start_date": str(date.today()),
            "custom_schedule": ["08:00", "20:00"],
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ordering_by_name(self):
        make_medication(self.patient, name="Zyrtec")
        make_medication(self.patient, name="Advil")
        self._auth(self.patient)
        response = self.client.get(self.list_url + "?ordering=name")
        names = [m["name"] for m in response.data["results"]]
        self.assertEqual(names, sorted(names))