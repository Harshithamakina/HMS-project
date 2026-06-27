from django.contrib import admin
from patients.models import PatientProfile

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'date_of_birth']
