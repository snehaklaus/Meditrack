from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from .models import Symptom, Moodlog
from .serializers import (
    SymptomSerializer,
    SymptomSummarySerializer,
    MoodLogSerializer,
    DoctorSymptomSerializer,
    DoctorMoodlogSerializer,
)
from medications.models import Medication

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


def make_symptom(user, **kwargs):
    defaults = dict(name="Headache", severity=5, date=date.today())
    defaults.update(kwargs)
    return Symptom.objects.create(user=user, **defaults)


def make_medication(user, **kwargs):
    defaults = dict(
        name="Aspirin",
        dosage="100mg",
        frequency="once_daily",
        start_date=date.today(),
    )
    defaults.update(kwargs)
    return Medication.objects.create(user=user, **defaults)


def make_moodlog(user, **kwargs):
    defaults = dict(mood=4, date=date.today())
    defaults.update(kwargs)
    return Moodlog.objects.create(user=user, **defaults)


# ─────────────────────────────────────────────
# Model Tests
# ─────────────────────────────────────────────

class SymptomModelTest(TestCase):
    def setUp(self):
        self.patient = make_patient()

    def test_str_representation(self):
        symptom = make_symptom(self.patient)
        self.assertIn("Headache", str(symptom))
        self.assertIn("5", str(symptom))
        self.assertIn(self.patient.username, str(symptom))

    def test_ordering_newest_first(self):
        s1 = make_symptom(self.patient, date=date.today() - timedelta(days=2))
        s2 = make_symptom(self.patient, date=date.today())
        symptoms = list(Symptom.objects.filter(user=self.patient))
        self.assertEqual(symptoms[0], s2)

    def test_related_medications_m2m(self):
        symptom = make_symptom(self.patient)
        med = make_medication(self.patient)
        symptom.related_medications.add(med)
        self.assertIn(med, symptom.related_medications.all())

    def test_notes_optional(self):
        symptom = make_symptom(self.patient, notes="")
        self.assertEqual(symptom.notes, "")

    def test_logged_at_auto_set(self):
        symptom = make_symptom(self.patient)
        self.assertIsNotNone(symptom.logged_at)

    def test_severity_boundaries(self):
        low = make_symptom(self.patient, severity=1)
        high = make_symptom(self.patient, severity=10)
        self.assertEqual(low.severity, 1)
        self.assertEqual(high.severity, 10)

    def test_backdating_allowed(self):
        past_date = date.today() - timedelta(days=30)
        symptom = make_symptom(self.patient, date=past_date)
        self.assertEqual(symptom.date, past_date)


class MoodlogModelTest(TestCase):
    def setUp(self):
        self.patient = make_patient()

    def test_str_representation(self):
        mood = make_moodlog(self.patient)
        self.assertIn(self.patient.username, str(mood))
        self.assertIn(str(date.today()), str(mood))

    def test_unique_per_day(self):
        make_moodlog(self.patient, date=date.today())
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            make_moodlog(self.patient, date=date.today())

    def test_ordering_newest_date_first(self):
        m1 = make_moodlog(self.patient, date=date.today() - timedelta(days=1))
        m2 = make_moodlog(self.patient, date=date.today())
        moods = list(Moodlog.objects.filter(user=self.patient))
        self.assertEqual(moods[0], m2)

    def test_mood_choices_valid(self):
        valid_moods = [1, 2, 3, 4, 5]
        for i, mood_val in enumerate(valid_moods):
            m = Moodlog.objects.create(
                user=self.patient,
                mood=mood_val,
                date=date.today() - timedelta(days=i + 1),
            )
            self.assertEqual(m.mood, mood_val)

    def test_notes_optional(self):
        mood = make_moodlog(self.patient, notes="")
        self.assertEqual(mood.notes, "")

    def test_cascade_delete_with_user(self):
        make_moodlog(self.patient)
        self.patient.delete()
        self.assertEqual(Moodlog.objects.count(), 0)


# ─────────────────────────────────────────────
# Serializer Tests
# ─────────────────────────────────────────────

class SymptomSerializerTest(TestCase):
    def setUp(self):
        self.patient = make_patient()

    def _context(self):
        request = MagicMock()
        request.user = self.patient
        return {"request": request}

    def test_valid_data_passes(self):
        data = {"name": "Nausea", "severity": 6, "date": str(date.today())}
        s = SymptomSerializer(data=data, context=self._context())
        self.assertTrue(s.is_valid(), s.errors)

    def test_future_date_invalid(self):
        data = {
            "name": "Nausea",
            "severity": 5,
            "date": str(date.today() + timedelta(days=1)),
        }
        s = SymptomSerializer(data=data, context=self._context())
        self.assertFalse(s.is_valid())
        self.assertIn("date", s.errors)

    def test_severity_below_1_invalid(self):
        data = {"name": "Pain", "severity": 0, "date": str(date.today())}
        s = SymptomSerializer(data=data, context=self._context())
        self.assertFalse(s.is_valid())

    def test_severity_above_10_invalid(self):
        data = {"name": "Pain", "severity": 11, "date": str(date.today())}
        s = SymptomSerializer(data=data, context=self._context())
        self.assertFalse(s.is_valid())

    def test_severity_boundary_1_valid(self):
        data = {"name": "Pain", "severity": 1, "date": str(date.today())}
        s = SymptomSerializer(data=data, context=self._context())
        self.assertTrue(s.is_valid(), s.errors)

    def test_severity_boundary_10_valid(self):
        data = {"name": "Pain", "severity": 10, "date": str(date.today())}
        s = SymptomSerializer(data=data, context=self._context())
        self.assertTrue(s.is_valid(), s.errors)

    def test_today_date_valid(self):
        data = {"name": "Fatigue", "severity": 3, "date": str(date.today())}
        s = SymptomSerializer(data=data, context=self._context())
        self.assertTrue(s.is_valid(), s.errors)

    def test_related_medications_details_present(self):
        symptom = make_symptom(self.patient)
        med = make_medication(self.patient)
        symptom.related_medications.add(med)
        s = SymptomSerializer(symptom, context=self._context())
        self.assertIn("related_medications_details", s.data)

    def test_html_in_name_rejected(self):
        data = {
            "name": "<script>alert(1)</script>",
            "severity": 5,
            "date": str(date.today()),
        }
        s = SymptomSerializer(data=data, context=self._context())
        self.assertFalse(s.is_valid())


class MoodLogSerializerTest(TestCase):
    def setUp(self):
        self.patient = make_patient()

    def _context(self):
        request = MagicMock()
        request.user = self.patient
        return {"request": request}

    def test_valid_data_passes(self):
        data = {"mood": 4, "date": str(date.today())}
        s = MoodLogSerializer(data=data, context=self._context())
        self.assertTrue(s.is_valid(), s.errors)

    def test_mood_display_read_only(self):
        mood = make_moodlog(self.patient)
        s = MoodLogSerializer(mood, context=self._context())
        self.assertIn("mood_display", s.data)
        self.assertEqual(s.data["mood_display"], "Good")

    def test_invalid_mood_value(self):
        data = {"mood": 99, "date": str(date.today())}
        s = MoodLogSerializer(data=data, context=self._context())
        self.assertFalse(s.is_valid())

    def test_user_is_hidden(self):
        mood = make_moodlog(self.patient)
        s = MoodLogSerializer(mood, context=self._context())
        self.assertNotIn("user", s.data)


class SymptomSummarySerializerTest(TestCase):
    def test_serializes_aggregated_data(self):
        # SymptomSummarySerializer is read-only (used with QuerySet .values()),
        # so test it by passing an object-like dict directly, not via is_valid()
        data = {
            "name": "Headache",
            "avg_severity": 6.5,
            "count": 3,
            "last_occurrence": date.today(),
        }
        s = SymptomSummarySerializer(data)
        self.assertEqual(s.data["symptom_name"], "Headache")
        self.assertEqual(s.data["avg_severity"], 6.5)
        self.assertEqual(s.data["count"], 3)


class DoctorSymptomSerializerTest(TestCase):
    def setUp(self):
        self.patient = make_patient()

    def test_related_medication_names(self):
        symptom = make_symptom(self.patient)
        med = make_medication(self.patient, name="Aspirin")
        symptom.related_medications.add(med)
        s = DoctorSymptomSerializer(symptom)
        self.assertIn("Aspirin", s.data["related_medication_names"])

    def test_fields_present(self):
        symptom = make_symptom(self.patient)
        s = DoctorSymptomSerializer(symptom)
        for field in ["id", "name", "severity", "notes", "date", "logged_at"]:
            self.assertIn(field, s.data)


# ─────────────────────────────────────────────
# View / API Tests — SymptomViewSet
# ─────────────────────────────────────────────

class SymptomViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = make_patient()
        self.other_patient = make_patient(username="patient2")
        self.doctor = make_doctor()
        self.doctor.assigned_patients.add(self.patient)

        self.symptom = make_symptom(self.patient)
        self.list_url = "/api/symptoms/"

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Auth ---

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Patient CRUD ---

    def test_patient_can_list_own_symptoms(self):
        self._auth(self.patient)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_patient_cannot_see_other_patient_symptoms(self):
        make_symptom(self.other_patient, name="Other Symptom")
        self._auth(self.patient)
        response = self.client.get(self.list_url)
        names = [s["name"] for s in response.data]
        self.assertNotIn("Other Symptom", names)

    def test_patient_can_create_symptom(self):
        self._auth(self.patient)
        payload = {"name": "Nausea", "severity": 7, "date": str(date.today())}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Symptom.objects.filter(user=self.patient).count(), 2)

    def test_patient_can_update_own_symptom(self):
        self._auth(self.patient)
        url = f"{self.list_url}{self.symptom.id}/"
        response = self.client.patch(url, {"severity": 9})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.symptom.refresh_from_db()
        self.assertEqual(self.symptom.severity, 9)

    def test_patient_can_delete_own_symptom(self):
        self._auth(self.patient)
        url = f"{self.list_url}{self.symptom.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_patient_cannot_access_other_symptom(self):
        other = make_symptom(self.other_patient, name="Hidden")
        self._auth(self.patient)
        url = f"{self.list_url}{other.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Doctor access ---

    def test_doctor_can_view_assigned_patient_symptoms(self):
        self._auth(self.doctor)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_doctor_cannot_see_unassigned_patient_symptoms(self):
        make_symptom(self.other_patient, name="Unassigned")
        self._auth(self.doctor)
        response = self.client.get(self.list_url)
        names = [s["name"] for s in response.data]
        self.assertNotIn("Unassigned", names)

    # --- Filtering ---

    def test_filter_by_severity(self):
        make_symptom(self.patient, name="Mild", severity=2)
        self._auth(self.patient)
        response = self.client.get(self.list_url + "?severity=2")
        for s in response.data:
            self.assertEqual(s["severity"], 2)

    def test_search_by_name(self):
        make_symptom(self.patient, name="Dizziness")
        self._auth(self.patient)
        response = self.client.get(self.list_url + "?search=Dizziness")
        names = [s["name"] for s in response.data]
        self.assertIn("Dizziness", names)

    def test_ordering_by_severity(self):
        make_symptom(self.patient, severity=1)
        make_symptom(self.patient, severity=9)
        self._auth(self.patient)
        response = self.client.get(self.list_url + "?ordering=severity")
        severities = [s["severity"] for s in response.data]
        self.assertEqual(severities, sorted(severities))

    # --- Custom Actions ---

    def test_last_seven_days_returns_recent(self):
        make_symptom(self.patient, name="Recent", date=date.today() - timedelta(days=3))
        make_symptom(self.patient, name="Old", date=date.today() - timedelta(days=30))
        self._auth(self.patient)
        response = self.client.get(self.list_url + "last_seven_days/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [s["name"] for s in response.data]
        self.assertIn("Recent", names)
        self.assertNotIn("Old", names)

    def test_summary_action_returns_aggregated_data(self):
        make_symptom(self.patient, name="Headache", severity=5)
        make_symptom(self.patient, name="Headache", severity=7)
        self._auth(self.patient)
        response = self.client.get(self.list_url + "summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [s["symptom_name"] for s in response.data]
        self.assertIn("Headache", names)

    def test_by_medication_requires_medication_id(self):
        self._auth(self.patient)
        response = self.client.get(self.list_url + "by_medication/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_by_medication_filters_correctly(self):
        med = make_medication(self.patient)
        s = make_symptom(self.patient, name="Med Related")
        s.related_medications.add(med)
        make_symptom(self.patient, name="Unrelated")
        self._auth(self.patient)
        response = self.client.get(
            self.list_url + f"by_medication/?medication_id={med.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [sym["name"] for sym in response.data]
        self.assertIn("Med Related", names)
        self.assertNotIn("Unrelated", names)

    # --- Validation ---

    def test_future_date_rejected(self):
        self._auth(self.patient)
        payload = {
            "name": "Future Pain",
            "severity": 5,
            "date": str(date.today() + timedelta(days=1)),
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_severity_out_of_range_rejected(self):
        self._auth(self.patient)
        payload = {"name": "Pain", "severity": 15, "date": str(date.today())}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- AI Insights (mocked) ---

    @patch("symptoms.views.HealthInsightsAI")
    def test_ai_insights_returns_200(self, MockAI):
        MockAI.return_value.analyze_symptoms.return_value = {
            "summary": "You seem healthy",
            "recommendations": [],
        }
        self._auth(self.patient)
        response = self.client.get(self.list_url + "ai_insights/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("cached", response.data)

    @patch("symptoms.views.HealthInsightsAI")
    def test_ai_insights_invalid_days_defaults_to_7(self, MockAI):
        MockAI.return_value.analyze_symptoms.return_value = {"summary": "ok"}
        self._auth(self.patient)
        response = self.client.get(self.list_url + "ai_insights/?days=notanumber")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("symptoms.views.cache")
    @patch("symptoms.views.HealthInsightsAI")
    def test_ai_insights_uses_cache_on_second_call(self, MockAI, mock_cache):
        cached_data = {"summary": "Cached", "cached": True}
        mock_cache.get.return_value = cached_data
        self._auth(self.patient)
        response = self.client.get(self.list_url + "ai_insights/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        MockAI.return_value.analyze_symptoms.assert_not_called()


# ─────────────────────────────────────────────
# View / API Tests — MoodLogViewSet
# ─────────────────────────────────────────────

class MoodLogViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = make_patient()
        self.other_patient = make_patient(username="patient2")
        self.list_url = "/api/moods/"

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_can_list_own_moods(self):
        make_moodlog(self.patient)
        self._auth(self.patient)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patient_cannot_see_other_moods(self):
        make_moodlog(self.other_patient)
        self._auth(self.patient)
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 0)

    def test_patient_can_create_mood(self):
        self._auth(self.patient)
        payload = {"mood": 5, "date": str(date.today())}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_mood_same_day_rejected(self):
        make_moodlog(self.patient, date=date.today())
        self._auth(self.patient)
        payload = {"mood": 3, "date": str(date.today())}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_trends_action_returns_chart_data(self):
        make_moodlog(self.patient, date=date.today() - timedelta(days=1))
        make_moodlog(self.patient, date=date.today())
        self._auth(self.patient)
        response = self.client.get(self.list_url + "trends/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("labels", response.data)
        self.assertIn("datasets", response.data)

    def test_trends_custom_days_param(self):
        self._auth(self.patient)
        response = self.client.get(self.list_url + "trends/?days=14")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mood_can_be_updated(self):
        mood = make_moodlog(self.patient)
        self._auth(self.patient)
        url = f"{self.list_url}{mood.id}/"
        response = self.client.patch(url, {"mood": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mood_can_be_deleted(self):
        mood = make_moodlog(self.patient)
        self._auth(self.patient)
        url = f"{self.list_url}{mood.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
# View / API Tests — export_health_report
# ─────────────────────────────────────────────

class ExportHealthReportTest(APITestCase):
    """
    URL: symptoms/urls.py → path('reports/export/', export_health_report, name='export-health-report')
    Included in config/urls.py as path('api/', include('symptoms.urls'))
    Resolved via reverse('export-health-report') → /api/reports/export/
    """
    def setUp(self):
        from django.urls import reverse
        self.client = APIClient()
        self.patient = make_patient()
        self.doctor = make_doctor()
        self.url = reverse("export-health-report")

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_doctor_cannot_export_report(self):
        self._auth(self.doctor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("symptoms.views.generate_health_report")
    def test_patient_can_export_report(self, mock_report):
        mock_report.return_value = b"%PDF-1.4 fake pdf bytes"
        self._auth(self.patient)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    @patch("symptoms.views.generate_health_report")
    def test_export_uses_default_30_days(self, mock_report):
        mock_report.return_value = b"%PDF fake"
        self._auth(self.patient)
        self.client.get(self.url)
        mock_report.assert_called_once_with(self.patient, days=30)

    @patch("symptoms.views.generate_health_report")
    def test_export_custom_days_param(self, mock_report):
        mock_report.return_value = b"%PDF fake"
        self._auth(self.patient)
        self.client.get(f"{self.url}?days=60")
        mock_report.assert_called_once_with(self.patient, days=60)

    @patch("symptoms.views.generate_health_report")
    def test_export_days_clamped_to_365(self, mock_report):
        mock_report.return_value = b"%PDF fake"
        self._auth(self.patient)
        self.client.get(f"{self.url}?days=9999")
        mock_report.assert_called_once_with(self.patient, days=365)

    @patch("symptoms.views.generate_health_report")
    def test_export_invalid_days_defaults_to_30(self, mock_report):
        mock_report.return_value = b"%PDF fake"
        self._auth(self.patient)
        self.client.get(f"{self.url}?days=notanumber")
        mock_report.assert_called_once_with(self.patient, days=30)

    @patch("symptoms.views.generate_health_report")
    def test_content_disposition_includes_username(self, mock_report):
        mock_report.return_value = b"%PDF fake"
        self._auth(self.patient)
        response = self.client.get(self.url)
        self.assertIn(self.patient.username, response["Content-Disposition"])