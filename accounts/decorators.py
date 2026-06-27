from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def doctor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_doctor():
            messages.error(request, 'Access denied. Doctor account required.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def patient_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_patient():
            messages.error(request, 'Access denied. Patient account required.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper
