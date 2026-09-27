from django.urls import path
from .views import BookingListCreateView, BookingDetailView, BookingCancelView

urlpatterns = [
    path('', BookingListCreateView.as_view(), name='booking-list'),
    path('<str:pk>/', BookingDetailView.as_view(), name='booking-detail'),
    path('<str:pk>/cancel/', BookingCancelView.as_view(), name='booking-cancel'),
]
