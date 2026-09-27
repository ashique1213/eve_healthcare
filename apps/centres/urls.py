from django.urls import path
from .views import (
    DiagnosticCentreListCreateView,
    DiagnosticCentreDetailView,
    DiagnosticTestListCreateView,
    DiagnosticTestDetailView,
    CentreTestListCreateView,
    CentreTestDetailView,
)

urlpatterns = [
    # Tests endpoints
    path('tests/', DiagnosticTestListCreateView.as_view(), name='diagnostic-tests-list'),
    path('tests/<str:pk>/', DiagnosticTestDetailView.as_view(), name='diagnostic-tests-detail'),

    # Pricing endpoints
    path('pricings/', CentreTestListCreateView.as_view(), name='centre-tests-list'),
    path('pricings/<str:pk>/', CentreTestDetailView.as_view(), name='centre-tests-detail'),

    # Centres endpoints
    path('', DiagnosticCentreListCreateView.as_view(), name='diagnostic-centres-list'),
    path('<str:pk>/', DiagnosticCentreDetailView.as_view(), name='diagnostic-centres-detail'),
]
