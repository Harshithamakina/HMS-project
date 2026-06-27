from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import patient_required
from patients.models import PatientProfile
from doctors.models import DoctorProfile, AvailabilitySlot
from bookings.models import Booking


@patient_required
def dashboard(request):
    patient = get_object_or_404(PatientProfile, user=request.user)
    today = timezone.now().date()

    upcoming_bookings = Booking.objects.filter(
        patient=patient,
        status='CONFIRMED',
        slot__date__gte=today
    ).select_related('slot__doctor__user', 'slot').order_by('slot__date', 'slot__start_time')[:5]

    total_bookings = Booking.objects.filter(patient=patient, status='CONFIRMED').count()

    context = {
        'patient': patient,
        'upcoming_bookings': upcoming_bookings,
        'total_bookings': total_bookings,
        'google_connected': bool(request.user.google_access_token),
    }
    return render(request, 'patients/dashboard.html', context)


@patient_required
def browse_doctors(request):
    today = timezone.now().date()

    # Only show doctors who have future available slots
    doctors = DoctorProfile.objects.filter(
        slots__is_available=True,
        slots__date__gte=today
    ).distinct()

    specialization = request.GET.get('specialization', '')
    if specialization:
        doctors = doctors.filter(specialization__icontains=specialization)

    specializations = DoctorProfile.objects.values_list('specialization', flat=True).distinct()

    return render(request, 'patients/browse_doctors.html', {
        'doctors': doctors,
        'specializations': specializations,
        'selected_specialization': specialization,
    })


@patient_required
def doctor_slots(request, doctor_id):
    patient = get_object_or_404(PatientProfile, user=request.user)
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    today = timezone.now().date()

    # Only future available slots
    slots = AvailabilitySlot.objects.filter(
        doctor=doctor,
        is_available=True,
        date__gte=today
    ).order_by('date', 'start_time')

    return render(request, 'patients/doctor_slots.html', {
        'doctor': doctor,
        'slots': slots,
        'patient': patient,
    })


@patient_required
def my_bookings(request):
    patient = get_object_or_404(PatientProfile, user=request.user)
    today = timezone.now().date()

    bookings = Booking.objects.filter(
        patient=patient
    ).select_related('slot__doctor__user', 'slot').order_by('slot__date', 'slot__start_time')

    return render(request, 'patients/my_bookings.html', {
        'bookings': bookings,
        'patient': patient,
        'today': today,
    })
