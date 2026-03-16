# fhir_integration/serializers.py
"""
FHIR R4 Serializers - Convert MediTrack models to FHIR resources
Maps User → Patient, Medication → Medication + MedicationStatement, Symptom → Observation
"""

from rest_framework import serializers
from accounts.models import User
from medications.models import Medication
from symptoms.models import Symptom, Moodlog
from datetime import datetime
import logging

logger = logging.getLogger('fhir_integration')


class FHIRPatientSerializer(serializers.ModelSerializer):
    """Convert MediTrack User to FHIR Patient Resource"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'date_of_birth', 'first_name', 'last_name']
    
    def to_fhir(self):
        """Convert Django user to FHIR Patient JSON"""
        user = self.instance
        
        # Build name from username or first/last name
        name_parts = []
        if user.first_name:
            name_parts.append(user.first_name)
        if user.last_name:
            name_parts.append(user.last_name)
        
        given_name = user.first_name or user.username.split()[0] if user.username else "Patient"
        family_name = user.last_name or (user.username.split()[-1] if user.username and ' ' in user.username else "")
        
        fhir_patient = {
            "resourceType": "Patient",
            "id": str(user.id),
            "identifier": [
                {
                    "system": "https://meditrack.up.railway.app/fhir/Patient",
                    "value": str(user.id)
                }
            ],
            "name": [
                {
                    "use": "official",
                    "given": [given_name],
                    "family": family_name
                }
            ],
            "telecom": [
                {
                    "system": "email",
                    "value": user.email,
                    "use": "work"
                }
            ],
            "gender": "unknown",  # Could extend User model to include gender
            "birthDate": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "active": user.is_active,
            "meta": {
                "lastUpdated": datetime.now().isoformat() + "Z",
                "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
            }
        }
        
        # Add phone if available
        if user.phone:
            fhir_patient["telecom"].append({
                "system": "phone",
                "value": user.phone,
                "use": "mobile"
            })
        
        return fhir_patient


class FHIRMedicationSerializer(serializers.ModelSerializer):
    """Convert MediTrack Medication to FHIR Medication & MedicationStatement"""
    
    class Meta:
        model = Medication
        fields = ['id', 'name', 'dosage', 'frequency', 'custom_schedule', 'start_date', 'end_date', 'notes', 'is_active']
    
    def to_fhir_medication_resource(self):
        """Create FHIR Medication resource"""
        med = self.instance
        
        return {
            "resourceType": "Medication",
            "id": f"med-{med.id}",
            "code": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": str(med.id),  # In production, map to RxNorm code
                        "display": med.name
                    }
                ],
                "text": med.name
            },
            "status": "active",
            "form": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "385055001",
                        "display": "Tablet"
                    }
                ]
            },
            "meta": {
                "lastUpdated": med.created_at.isoformat() + "Z",
                "profile": ["http://hl7.org/fhir/StructureDefinition/Medication"]
            }
        }
    
    def to_fhir_medication_statement(self, patient_id):
        """Create FHIR MedicationStatement resource"""
        med = self.instance
        
        # Parse frequency to timing information
        frequency_mapping = {
            'once_daily': {'frequency': 1, 'period': 1, 'periodUnit': 'd'},
            'twice_daily': {'frequency': 2, 'period': 1, 'periodUnit': 'd'},
            'three_times_daily': {'frequency': 3, 'period': 1, 'periodUnit': 'd'},
            'as_needed': {'frequency': 1, 'period': 1, 'periodUnit': 'd'},
            'custom': {'frequency': 1, 'period': 1, 'periodUnit': 'd'},
        }
        
        timing_info = frequency_mapping.get(med.frequency, {'frequency': 1, 'period': 1, 'periodUnit': 'd'})
        dosage_text = f"{med.dosage} {med.get_frequency_display()}" if med.dosage else "As prescribed"
        
        statement = {
            "resourceType": "MedicationStatement",
            "id": f"medstmt-{med.id}",
            "status": "active" if med.is_active and not med.end_date else "completed",
            "medicationReference": {
                "reference": f"Medication/med-{med.id}",
                "display": med.name
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "type": "Patient"
            },
            "effectivePeriod": {
                "start": med.start_date.isoformat() if med.start_date else None,
                "end": med.end_date.isoformat() if med.end_date else None
            },
            "dateAsserted": med.created_at.isoformat() + "Z",
            "dosage": [
                {
                    "text": dosage_text,
                    "timing": {
                        "repeat": timing_info
                    },
                    "route": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "26643006",
                                "display": "Oral route"
                            }
                        ]
                    }
                }
            ],
            "note": [{"text": med.notes}] if med.notes else [],
            "meta": {
                "lastUpdated": med.updated_at.isoformat() + "Z",
                "profile": ["http://hl7.org/fhir/StructureDefinition/MedicationStatement"]
            }
        }
        
        # Add dosage quantity if parseable
        try:
            if med.dosage:
                dose_value = float(med.dosage.split()[0])
                statement["dosage"][0]["doseAndRate"] = [
                    {
                        "doseQuantity": {
                            "value": dose_value,
                            "unit": "mg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mg"
                        }
                    }
                ]
        except (ValueError, IndexError):
            # If dosage parsing fails, just skip doseAndRate
            pass
        
        return statement


class FHIRObservationSerializer(serializers.ModelSerializer):
    """Convert MediTrack Symptom to FHIR Observation"""
    
    class Meta:
        model = Symptom
        fields = ['id', 'name', 'severity', 'date', 'notes', 'logged_at']
    
    def to_fhir(self, patient_id):
        """Convert Symptom to FHIR Observation"""
        symptom = self.instance
        
        # Map symptom names to SNOMED CT codes (common symptoms)
        snomed_mappings = {
            'headache': '25064002',
            'dizziness': '404223003',
            'fatigue': '84445001',
            'nausea': '422587007',
            'vomiting': '422400008',
            'fever': '386661006',
            'cough': '49727002',
            'sore throat': '405737000',
            'difficulty breathing': '230145002',
            'chest pain': '29857009',
            'abdominal pain': '21522001',
            'anxiety': '48694002',
            'depression': '35489007',
            'insomnia': '193462001',
        }
        
        # Get SNOMED code or use generic finding code
        symptom_name_lower = symptom.name.lower().strip()
        snomed_code = snomed_mappings.get(symptom_name_lower, '418799008')
        
        observation = {
            "resourceType": "Observation",
            "id": f"obs-symptom-{symptom.id}",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": snomed_code,
                        "display": symptom.name
                    }
                ],
                "text": symptom.name
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "type": "Patient"
            },
            "effectiveDateTime": symptom.date.isoformat() + "T00:00:00Z",
            "issued": symptom.logged_at.isoformat() + "Z",
            "valueQuantity": {
                "value": symptom.severity,
                "unit": "on a scale of 0-10",
                "system": "http://unitsofmeasure.org",
                "code": "{score}"
            },
            "note": [{"text": symptom.notes}] if symptom.notes else [],
            "meta": {
                "lastUpdated": symptom.logged_at.isoformat() + "Z",
                "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"]
            }
        }
        
        return observation


class FHIRMoodObservationSerializer(serializers.ModelSerializer):
    """Convert MediTrack Moodlog to FHIR Observation (mental health)"""
    
    class Meta:
        model = Moodlog
        fields = ['id', 'mood', 'date', 'notes', 'logged_at']
    
    def to_fhir(self, patient_id):
        """Convert Moodlog to FHIR Observation"""
        mood = self.instance
        
        mood_text_map = {
            1: 'Very Bad',
            2: 'Bad',
            3: 'Okay',
            4: 'Good',
            5: 'Very Good',
        }
        
        observation = {
            "resourceType": "Observation",
            "id": f"obs-mood-{mood.id}",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "mental-health",
                            "display": "Mental Health"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "14323008",
                        "display": "Mood"
                    }
                ],
                "text": "Mood Assessment"
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "type": "Patient"
            },
            "effectiveDateTime": mood.date.isoformat() + "T00:00:00Z",
            "issued": mood.logged_at.isoformat() + "Z",
            "valueQuantity": {
                "value": mood.mood,
                "unit": "on a scale of 1-5",
                "system": "http://unitsofmeasure.org",
                "code": "{score}"
            },
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": mood_text_map.get(mood.mood, 'U'),
                            "display": mood.get_mood_display()
                        }
                    ]
                }
            ],
            "note": [{"text": mood.notes}] if mood.notes else [],
            "meta": {
                "lastUpdated": mood.logged_at.isoformat() + "Z",
                "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"]
            }
        }
        
        return observation
