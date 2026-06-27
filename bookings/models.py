from django.db import models
from doctors.models import AvailabilitySlot
from patients.models import PatientProfile


class Booking(models.Model):
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_NO_SHOW = 'NO_SHOW'
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_NO_SHOW, 'No Show'),
    ]

    # OneToOne ensures one booking per slot — enforced at DB level
    slot = models.OneToOneField(AvailabilitySlot, on_delete=models.CASCADE, related_name='booking')
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient} → {self.slot}"


class CalendarEventLog(models.Model):
    """
    Tracks calendar event creation per booking.
    Real world value: when Google token expires and event creation
    silently fails, this table shows exactly which bookings have
    no calendar event — enabling targeted retry.
    """
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='calendar_log')
    doctor_event_id = models.CharField(max_length=200, blank=True, null=True)
    patient_event_id = models.CharField(max_length=200, blank=True, null=True)
    doctor_event_created = models.BooleanField(default=False)
    patient_event_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"CalendarLog for Booking #{self.booking.id}"


class NotificationLog(models.Model):
    """
    Every email attempt is logged here.
    Silent failures are now visible — not invisible.
    """
    EVENT_SIGNUP = 'SIGNUP_WELCOME'
    EVENT_BOOKING = 'BOOKING_CONFIRMATION'
    EVENT_CANCELLATION = 'BOOKING_CANCELLATION'
    EVENT_CHOICES = [
        (EVENT_SIGNUP, 'Signup Welcome'),
        (EVENT_BOOKING, 'Booking Confirmation'),
        (EVENT_CANCELLATION, 'Booking Cancellation'),
    ]

    STATUS_SENT = 'SENT'
    STATUS_FAILED = 'FAILED'
    STATUS_PENDING = 'PENDING'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_PENDING, 'Pending'),
    ]

    user_email = models.EmailField()
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    retry_count = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} → {self.user_email} [{self.status}]"
