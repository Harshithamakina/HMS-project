from django.contrib import admin
from bookings.models import Booking, CalendarEventLog, NotificationLog

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'slot', 'status', 'created_at']
    list_filter = ['status']

@admin.register(CalendarEventLog)
class CalendarEventLogAdmin(admin.ModelAdmin):
    list_display = ['booking', 'doctor_event_created', 'patient_event_created', 'error_message']

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'event_type', 'status', 'retry_count', 'sent_at']
    list_filter = ['status', 'event_type']
