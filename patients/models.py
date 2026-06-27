from django.db import models
from accounts.models import User


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)

    def __str__(self):
        return f"Patient: {self.user.get_full_name() or self.user.email}"
