from rest_framework import serializers
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'phone', 'date_of_birth']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'role': {'required': False},
            'phone': {'required': False},
            'date_of_birth': {'required': False},
        }
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'patient'),
            phone=validated_data.get('phone', ''),
            date_of_birth=validated_data.get('date_of_birth', None),
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone', 'date_of_birth']


class PatientSerializer(serializers.ModelSerializer):
    assigned_doctor_name = serializers.CharField(
        source='assigned_doctor.username',
        read_only=True
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'date_of_birth', 'assigned_doctor', 'assigned_doctor_name']


class DoctorPatientsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'date_of_birth']