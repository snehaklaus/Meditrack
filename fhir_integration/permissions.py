from rest_framework.permissions import BasePermission,IsAuthenticated
import logging


logger = logging.getLogger('fhir_integration')


class IsFHIRAuthenticated(IsAuthenticated):
    def has_permission(self, request, view):
        is_auth=super().has_permission(request,view)
        if not is_auth:
            logger.warning(f"Unauthorized FHIR access attempt from{request.META.get('REMOTE_ADDR')}")
        return is_auth


class CanAccessOwnPatientData(BasePermission):
    message="You can only access your own patient data"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj,'user'):
            return obj.user==request.user
        
        logger.warning(f"Permission checked failed for unknown object type:{type(obj)}")
        return False

class HasFHIRScope(BasePermission):
    required_scope=None
    message="You do not have the required FHIR scope for this action."


    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not self.required_scope:
            return True
        

class IsDoctorOrPatient(BasePermission):
    message="Invalid user role for FHIR access"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        if request.user.role=='patient':
            if hasattr(obj,'user'):
                return obj.user==request.user
            return obj==request.user
        
        elif request.user.role=='doctor':
            if hasattr(obj,'user'):
                patient=obj.user
            else:
                patient=obj

            return patient.assigned_doctor==request.user
        return False