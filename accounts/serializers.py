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
        fields = ['id', 'username', 'email', 'role', 'phone', 'date_of_birth', 'email_digest_enabled', 'preferred_language']  # ⭐ Add preferred_language
        read_only_fields = ['id', 'role']
        
    def validate_username(self, value):
        """Ensure username is unique when updating"""
        user = self.instance
        if user and User.objects.filter(username=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('Username already taken')
        return value
    
    def validate_email(self, value):
        """Ensure email is unique when updating"""
        user = self.instance
        if user and User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('Email already taken')
        return value
    
    def validate_phone(self, value):
        """Basic phone validation"""
        if value and len(value.strip()) > 0:
            # Remove common characters
            cleaned = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
            if not cleaned.isdigit():
                raise serializers.ValidationError('Phone number should contain only digits, spaces, and +()-')
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise serializers.ValidationError('Phone number should be between 7 and 15 digits')
        return value
    
    def validate_date_of_birth(self, value):
        """Ensure date of birth is valid"""
        if value:
            from datetime import date
            today = date.today()
            if value > today:
                raise serializers.ValidationError('Date of birth cannot be in the future')
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age > 150:
                raise serializers.ValidationError('Invalid date of birth')
            if age < 0:
                raise serializers.ValidationError('Date of birth cannot be in the future')
        return value


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