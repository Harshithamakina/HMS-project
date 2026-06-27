from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import doctor_required
from doctors.models import DoctorProfile, AvailabilitySlot
from doctors.forms import AvailabilitySlotForm
from bookings.models import Booking


@doctor_required
def dashboard(request):
    doctor = get_object_or_404(DoctorProfile, user=request.user)
    today = timezone.now().date()

    upcoming_slots = AvailabilitySlot.objects.filter(
        doctor=doctor,
        date__gte=today,
        is_available=True
    ).order_by('date', 'start_time')[:5]

    upcoming_bookings = Booking.objects.filter(
        slot__doctor=doctor,
        status='CONFIRMED',
        slot__date__gte=today
    ).select_related('patient__user', 'slot').order_by('slot__date', 'slot__start_time')[:5]

    total_slots = AvailabilitySlot.objects.filter(doctor=doctor).count()
    total_bookings = Booking.objects.filter(slot__doctor=doctor, status='CONFIRMED').count()

    context = {
        'doctor': doctor,
        'upcoming_slots': upcoming_slots,
        'upcoming_bookings': upcoming_bookings,
        'total_slots': total_slots,
        'total_bookings': total_bookings,
        'google_connected': bool(request.user.google_access_token),
    }
    return render(request, 'doctors/dashboard.html', context)


@doctor_required
def manage_slots(request):
    doctor = get_object_or_404(DoctorProfile, user=request.user)

    if request.method == 'POST':
        form = AvailabilitySlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.doctor = doctor
            try:
                slot.save()
                messages.success(request, f'Slot added: {slot.date} {slot.start_time} - {slot.end_time}')
            except Exception:
                messages.error(request, 'A slot already exists at that time. Choose a different time.')
            return redirect('doctors:manage_slots')
    else:
        form = AvailabilitySlotForm()

    today = timezone.now().date()
    slots = AvailabilitySlot.objects.filter(
        doctor=doctor,
        date__gte=today
    ).order_by('date', 'start_time')

    return render(request, 'doctors/manage_slots.html', {'form': form, 'slots': slots, 'doctor': doctor})


@doctor_required
def delete_slot(request, slot_id):
    doctor = get_object_or_404(DoctorProfile, user=request.user)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, doctor=doctor)

    if slot.is_available:
        slot.delete()
        messages.success(request, 'Slot removed.')
    else:
        messages.error(request, 'Cannot remove a booked slot.')

    return redirect('doctors:manage_slots')


@doctor_required
def my_bookings(request):
    doctor = get_object_or_404(DoctorProfile, user=request.user)
    today = timezone.now().date()

    bookings = Booking.objects.filter(
        slot__doctor=doctor
    ).select_related('patient__user', 'slot').order_by('slot__date', 'slot__start_time')

    return render(request, 'doctors/my_bookings.html', {'bookings': bookings, 'doctor': doctor, 'today': today})
