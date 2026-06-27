from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from accounts.forms import DoctorSignupForm, PatientSignupForm, LoginForm
from accounts.models import User
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from notifications.service import send_notification
import requests
import json


def signup_choose(request):
    return render(request, 'accounts/signup_choose.html')


def doctor_signup(request):
    if request.method == 'POST':
        form = DoctorSignupForm(request.POST)
        
        # Manually check license number BEFORE saving anything
        license_number = request.POST.get('license_number', '')
        from doctors.models import DoctorProfile
        if DoctorProfile.objects.filter(license_number=license_number).exists():
            messages.error(request, 'License number already registered. Use a different one.')
            return render(request, 'accounts/doctor_signup.html', {'form': form})

        if form.is_valid():
            user = form.save()
            DoctorProfile.objects.create(
                user=user,
                specialization=form.cleaned_data['specialization'],
                license_number=form.cleaned_data['license_number'],
            )
            send_notification(
                user_email=user.email,
                event_type='SIGNUP_WELCOME',
                payload={
                    'name': user.get_full_name(),
                    'role': 'Doctor',
                    'email': user.email,
                }
            )
            login(request, user)
            messages.success(request, 'Welcome, Doctor!')
            return redirect('doctors:dashboard')
    else:
        form = DoctorSignupForm()
    return render(request, 'accounts/doctor_signup.html', {'form': form})


def patient_signup(request):
    if request.method == 'POST':
        form = PatientSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            PatientProfile.objects.create(
                user=user,
                phone_number=form.cleaned_data.get('phone_number', ''),
                date_of_birth=form.cleaned_data.get('date_of_birth'),
            )
            send_notification(
                user_email=user.email,
                event_type='SIGNUP_WELCOME',
                payload={
                    'name': user.get_full_name(),
                    'role': 'Patient',
                    'email': user.email,
                }
            )
            login(request, user)
            messages.success(request, 'Welcome! You can now book appointments.')
            return redirect('patients:dashboard')
    else:
        form = PatientSignupForm()
    return render(request, 'accounts/patient_signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                return _redirect_by_role(user)
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


def _redirect_by_role(user):
    if user.is_doctor():
        return redirect('doctors:dashboard')
    return redirect('patients:dashboard')


# Google OAuth2 flow
def google_auth(request):
    import secrets
    from urllib.parse import urlencode
    
    # Store user id in session before redirect
    request.session['user_id_for_oauth'] = request.user.id
    request.session.save()
    
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    request.session.save()

    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/calendar.events',
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state,
    }

    auth_url = 'https://accounts.google.com/o/oauth2/auth?' + urlencode(params)
    return redirect(auth_url)

def google_callback(request):
    from accounts.models import User as UserModel
    
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Google auth failed — no code received.')
        return redirect('accounts:login')

    # Get user from session — works even if main session expired
    user_id = request.session.get('user_id_for_oauth')
    
    if not user_id and not request.user.is_authenticated:
        messages.error(request, 'Session expired. Please log in and try again.')
        return redirect('accounts:login')

    try:
        if request.user.is_authenticated:
            user = request.user
        else:
            user = UserModel.objects.get(id=user_id)
            # Re-login the user
            from django.contrib.auth import login as auth_login
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth_login(request, user)

        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code',
            }
        )
        token_data = token_response.json()

        if 'error' in token_data:
            messages.error(request, f'Google auth failed: {token_data.get("error_description", token_data["error"])}')
            return _redirect_by_role(user)

        user.google_access_token = token_data.get('access_token')
        user.google_refresh_token = token_data.get('refresh_token')
        user.save()
        messages.success(request, 'Google Calendar connected successfully!')

    except Exception as e:
        messages.error(request, f'Google Calendar connection failed: {str(e)}')
        return redirect('accounts:login')

    return _redirect_by_role(user)