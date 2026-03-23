from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


# One-time superuser creation
def create_initial_superuser():
    """Creates initial superuser if it doesn't exist"""
    try:
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_superuser(
                username='admin',
                email='sneha.naik1117@gmail.com',
                password='Admin123!@#'  # CHANGE THIS PASSWORD!
            )
            # Set role if required
            if hasattr(user, 'role'):
                user.role = 'patient'  # or leave blank if optional
                user.save()
            print('✅ Superuser "admin" created successfully!')
        else:
            print('ℹ️ Superuser "admin" already exists')
    except Exception as e:
        print(f'❌ Error creating superuser: {e}')


# Call it once when admin module loads
create_initial_superuser()


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