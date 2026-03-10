from rest_framework import serializers
from .models import Symptom,Moodlog
from medications.serializers import MedicationSerializer
from datetime import date

class SymptomSerializer(serializers.ModelSerializer):
       user = serializers.HiddenField(default=serializers.CurrentUserDefault())
       related_medications_details = MedicationSerializer(source='related_medications', many=True, read_only=True)
       
       class Meta:
           model = Symptom
           fields = '__all__'
           read_only_fields = ['logged_at']
       
       def validate_date(self, value):
           if value > date.today():
               raise serializers.ValidationError("Cannot log symptoms in the future")
           return value
       
       def validate_severity(self, value):
           if not 1 <= value <= 10:
               raise serializers.ValidationError("Severity must be between 1 and 10")
           return value

class SymptomSummarySerializer(serializers.Serializer):
       """For aggregated symptom data"""
       symptom_name = serializers.CharField(source="name")
       avg_severity = serializers.FloatField()
       count = serializers.IntegerField()
       last_occurrence = serializers.DateField()


class MoodLogSerializer(serializers.ModelSerializer):
     user=serializers.HiddenField(default=serializers.CurrentUserDefault())
     mood_display=serializers.CharField(source='get_mood_display',read_only=True)

     class Meta:
          model=Moodlog
          fields='__all__'
          read_only_fields=['logged_at']

class DoctorSymptomSerializer(serializers.ModelSerializer):
     related_medication_names=serializers.SerializerMethodField()

     class Meta:
          model = Symptom
          fields=[
               'id',
               'name',
               'severity',
               'notes',
               'date',
               'logged_at',
               'related_medications',
               'related_medication_names'
          ]
          read_only_fields=['id','logged_at']

     def get_related_medication_names(self,obj):
          return [med.name for med in obj.related_medications.all()]
     

class DoctorMoodlogSerializer(serializers.ModelSerializer):
     mood_display=serializers.CharField(source='get_mood_display',read_only=True)

     class Meta:
          model=Moodlog
          fields =[
               'id',
               'mood',
               'mood_display',
               'notes',
               'date',
               'logged_at'
          ]

          read_only_fields=['id','logged_at']