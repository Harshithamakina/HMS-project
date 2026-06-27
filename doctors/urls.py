from django.urls import path
from doctors import views

app_name = 'doctors'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('slots/', views.manage_slots, name='manage_slots'),
    path('slots/delete/<int:slot_id>/', views.delete_slot, name='delete_slot'),
    path('bookings/', views.my_bookings, name='my_bookings'),
]
