from django.urls import path

from . import views

urlpatterns = [
    path('bienestar/', views.BienestarView.as_view(), name='bienestar'),
    path('bienestar/citas/<int:pk>/cancelar/', views.CancelarCitaView.as_view(), name='bienestar_cancelar'),
    path('bienestar/<slug:servicio>/', views.ServicioView.as_view(), name='bienestar_servicio'),
    path('bienestar/<slug:servicio>/agendar/', views.AgendarView.as_view(), name='bienestar_agendar'),
]
