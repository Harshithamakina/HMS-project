from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import User


class DoctorSignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    specialization = forms.CharField(max_length=100, required=True)
    license_number = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']
    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        from doctors.models import DoctorProfile
        if DoctorProfile.objects.filter(license_number=license_number).exists():
            raise forms.ValidationError('This license number is already registered.')
        return license_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.role = User.ROLE_DOCTOR
        if commit:
            user.save()
        return user


class PatientSignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=10, required=False)
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.role = User.ROLE_PATIENT
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
