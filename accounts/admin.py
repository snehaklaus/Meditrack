from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User



@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'assigned_doctor', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_active']
    search_fields = ['username', 'email']
    
    # Add role to the fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'date_of_birth', 'assigned_doctor')}),
    )
    
    # Add role to add form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'date_of_birth')}),
    )