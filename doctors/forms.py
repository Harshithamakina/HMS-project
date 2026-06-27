from django import forms
from doctors.models import AvailabilitySlot
from django.utils import timezone
import datetime


class AvailabilitySlotForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySlot
        fields = ['date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if date and start_time and end_time:
            slot_datetime = datetime.datetime.combine(date, start_time)
            slot_datetime = timezone.make_aware(slot_datetime)
        if slot_datetime < timezone.now():
            raise forms.ValidationError('Cannot create slots in the past.')
            if start_time >= end_time:
                raise forms.ValidationError('Start time must be before end time.')

        return cleaned_data
