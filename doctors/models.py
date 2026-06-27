from django.db import models
from accounts.models import User


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.email}"

    def get_full_name(self):
        return self.user.get_full_name() or self.user.email


class AvailabilitySlot(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    # version field enables optimistic locking visibility in schema
    # actual locking done via select_for_update() in booking view
    version = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent duplicate slots for same doctor at same time
        unique_together = ['doctor', 'date', 'start_time']
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.doctor} - {self.date} {self.start_time}-{self.end_time}"

    def is_future(self):
        from django.utils import timezone
        import datetime
        slot_datetime = timezone.make_aware(
            datetime.datetime.combine(self.date, self.start_time)
        )
        return slot_datetime > timezone.now()
