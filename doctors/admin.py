from django.contrib import admin
from doctors.models import DoctorProfile, AvailabilitySlot

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'license_number']

@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'date', 'start_time', 'end_time', 'is_available']
    list_filter = ['is_available', 'date']
