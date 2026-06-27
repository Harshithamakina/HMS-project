from django.urls import path
from patients import views

app_name = 'patients'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('doctors/', views.browse_doctors, name='browse_doctors'),
    path('doctors/<int:doctor_id>/slots/', views.doctor_slots, name='doctor_slots'),
    path('bookings/', views.my_bookings, name='my_bookings'),
]
