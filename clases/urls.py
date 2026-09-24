from django.urls import path

from . import views

urlpatterns = [
    path('horarios/', views.HorariosView.as_view(), name='horarios'),
    path('horarios/simular/', views.SimularOcupacionView.as_view(), name='simular_ocupacion'),
    path('clases/<int:pk>/reservar/', views.ReservarView.as_view(), name='reservar'),
    path('reservas/<int:pk>/cancelar/', views.CancelarView.as_view(), name='cancelar_reserva'),
]
