from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_choose, name='signup_choose'),
    path('signup/doctor/', views.doctor_signup, name='doctor_signup'),
    path('signup/patient/', views.patient_signup, name='patient_signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('google/auth/', views.google_auth, name='google_auth'),
    path('google/callback/', views.google_callback, name='google_callback'),
]
