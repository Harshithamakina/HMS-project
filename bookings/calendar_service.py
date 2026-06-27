"""
Google Calendar integration service.
Creates calendar events for both doctor and patient on booking confirmation.

Real world problem addressed:
When a Google token expires and event creation silently fails,
CalendarEventLog tracks the failure. This means:
1. You can query: SELECT * FROM calendar_event_log WHERE doctor_event_created=False
2. You can build a retry job that re-attempts failed calendar creations
Without this log, you'd never know which bookings have no calendar event.
"""
import datetime
from django.conf import settings
from bookings.models import CalendarEventLog


def create_calendar_events(booking):
    """Creates calendar events for doctor and patient. Logs success/failure."""
    log = CalendarEventLog.objects.create(booking=booking)

    slot = booking.slot
    doctor = slot.doctor
    patient = booking.patient

    start_dt = datetime.datetime.combine(slot.date, slot.start_time).isoformat()
    end_dt = datetime.datetime.combine(slot.date, slot.end_time).isoformat()

    # Doctor calendar event
    try:
        doctor_event_id = _create_event(
            user=doctor.user,
            title=f'Appointment with {patient.user.get_full_name()}',
            start=start_dt,
            end=end_dt,
            description=f'Patient booking confirmed via HMS'
        )
        log.doctor_event_id = doctor_event_id
        log.doctor_event_created = True
    except Exception as e:
        print("Doctor calendar error:", e)
        log.error_message = f'Doctor calendar failed: {str(e)}'

    # Patient calendar event
    try:
        patient_event_id = _create_event(
            user=patient.user,
            title=f'Appointment with Dr. {doctor.user.get_full_name()}',
            start=start_dt,
            end=end_dt,
            description=f'Appointment with {doctor} — {doctor.specialization}'
        )
        log.patient_event_id = patient_event_id
        log.patient_event_created = True
    except Exception as e:
        print("Patient calendar error:", e)
        existing = log.error_message or ''
        log.error_message = existing + f' | Patient calendar failed: {str(e)}'

    log.save()
    return log


def _create_event(user, title, start, end, description=''):
    """
    Creates a Google Calendar event for a user.
    Handles token refresh — tokens expire after 1 hour.
    If no token exists, skips silently (user hasn't connected Google).
    """
    if not user.google_access_token:
        raise Exception('User has not connected Google Calendar')

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from django.utils import timezone

    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        user.google_access_token = creds.token
        user.google_token_expiry = creds.expiry
        user.save(update_fields=['google_access_token', 'google_token_expiry'])

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': title,
        'description': description,
        'start': {'dateTime': start, 'timeZone': 'Asia/Kolkata'},
        'end': {'dateTime': end, 'timeZone': 'Asia/Kolkata'},
    }

    created = service.events().insert(calendarId='primary', body=event).execute()
    return created.get('id')
