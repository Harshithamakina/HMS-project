from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from accounts.decorators import patient_required
from doctors.models import AvailabilitySlot, DoctorProfile
from patients.models import PatientProfile
from bookings.models import Booking, CalendarEventLog, NotificationLog
from notifications.service import send_notification
from bookings.calendar_service import create_calendar_events
import datetime


@patient_required
def book_slot(request, slot_id):
    """
    RACE CONDITION HANDLING:
    Two patients clicking at the same time both pass an is_available check
    if we only do a simple get() + check. We use select_for_update() inside
    an atomic transaction. This locks the DB row for Patient A's request.
    Patient B waits at the DB level. When Patient A commits, Patient B reads
    the updated is_available=False and returns an error.

    Design decision defended: pessimistic locking (select_for_update) over
    optimistic locking (version field check-then-update). In a booking system,
    contention is highest at peak times. A failed optimistic lock means showing
    an error and asking the patient to retry — bad UX. Pessimistic locking
    holds the row for milliseconds and gives Patient B a clean "already booked"
    message without requiring a retry.
    """
    if request.method != 'POST':
        return redirect('patients:browse_doctors')

    patient = get_object_or_404(PatientProfile, user=request.user)

    try:
        with transaction.atomic():
            # Lock this specific row — no other transaction can read/write it
            # until this block completes
            slot = AvailabilitySlot.objects.select_for_update().get(id=slot_id)

            # Check 1: Is slot still available?
            if not slot.is_available:
                messages.error(request, 'Sorry, this slot was just booked by someone else.')
                return redirect('patients:doctor_slots', doctor_id=slot.doctor.id)

            # Check 2: Is slot still in the future? (patient had page open for a while)
            if not slot.is_future():
                messages.error(request, 'This slot has already passed.')
                return redirect('patients:doctor_slots', doctor_id=slot.doctor.id)

            # Check 3: Does this patient already have a booking at this time?
            # Real world: patient books two doctors at the same time
            conflicting = Booking.objects.filter(
                patient=patient,
                status='CONFIRMED',
                slot__date=slot.date,
                slot__start_time=slot.start_time,
            ).exists()

            if conflicting:
                messages.error(request, 'You already have an appointment at this time.')
                return redirect('patients:doctor_slots', doctor_id=slot.doctor.id)

            # All checks passed — create the booking
            slot.is_available = False
            slot.version += 1
            slot.save()

            booking = Booking.objects.create(slot=slot, patient=patient)

    except AvailabilitySlot.DoesNotExist:
        messages.error(request, 'Slot not found.')
        return redirect('patients:browse_doctors')

    # Outside transaction: Google Calendar + email
    # These are best-effort — booking is confirmed regardless
    # Failures are logged in CalendarEventLog and NotificationLog
    _post_booking_tasks(booking, slot, patient)

    messages.success(request, f'Appointment confirmed with {slot.doctor} on {slot.date} at {slot.start_time}.')
    return redirect('patients:my_bookings')


def _post_booking_tasks(booking, slot, patient):
    """
    Calendar creation and email notification happen outside the DB transaction.
    This is intentional: if Google Calendar is down, the booking still succeeds.
    Failures are tracked in CalendarEventLog and NotificationLog for visibility.
    """
    # Google Calendar
    create_calendar_events(booking)

    # Email confirmation to patient
    send_notification(
        user_email=patient.user.email,
        event_type='BOOKING_CONFIRMATION',
        payload={
            'patient_name': patient.user.get_full_name(),
            'doctor_name': str(slot.doctor),
            'date': str(slot.date),
            'start_time': str(slot.start_time),
            'end_time': str(slot.end_time),
        }
    )

    # Email notification to doctor
    send_notification(
        user_email=slot.doctor.user.email,
        event_type='BOOKING_CONFIRMATION',
        payload={
            'patient_name': patient.user.get_full_name(),
            'doctor_name': str(slot.doctor),
            'date': str(slot.date),
            'start_time': str(slot.start_time),
            'end_time': str(slot.end_time),
        }
    )


@patient_required
def cancel_booking(request, booking_id):
    """
    Cancellation releases the slot so other patients can book it.
    Without this, no-shows permanently block doctor availability.
    """
    patient = get_object_or_404(PatientProfile, user=request.user)
    booking = get_object_or_404(Booking, id=booking_id, patient=patient)

    if booking.status != 'CONFIRMED':
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('patients:my_bookings')

    with transaction.atomic():
        booking.status = 'CANCELLED'
        booking.save()
        # Release the slot
        booking.slot.is_available = True
        booking.slot.save()

    send_notification(
        user_email=patient.user.email,
        event_type='BOOKING_CANCELLATION',
        payload={
            'patient_name': patient.user.get_full_name(),
            'doctor_name': str(booking.slot.doctor),
            'date': str(booking.slot.date),
        }
    )

    messages.success(request, 'Booking cancelled. The slot is now available for others.')
    return redirect('patients:my_bookings')
