from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'get_full_name', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    fieldsets = UserAdmin.fieldsets + (
        ('HMS Info', {'fields': ('role', 'google_access_token', 'google_refresh_token')}),
    )
