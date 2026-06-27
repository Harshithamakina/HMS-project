from django.urls import path
from bookings import views

app_name = 'bookings'

urlpatterns = [
    path('book/<int:slot_id>/', views.book_slot, name='book_slot'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
]
