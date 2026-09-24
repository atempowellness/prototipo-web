from django.urls import path

from . import views

urlpatterns = [
    path('horarios/', views.HorariosView.as_view(), name='horarios'),
    path('horarios/simular/', views.SimularOcupacionView.as_view(), name='simular_ocupacion'),
    path('clases/<int:pk>/reservar/', views.ReservarView.as_view(), name='reservar'),
    path('reservas/<int:pk>/cancelar/', views.CancelarView.as_view(), name='cancelar_reserva'),
    # Lista de espera
    path('clases/<int:pk>/lista-de-espera/', views.AnotarseView.as_view(), name='anotarse_espera'),
    path('clases/<int:pk>/simular-cupo/', views.SimularCupoView.as_view(), name='simular_cupo'),
    path('lista-de-espera/<int:pk>/salir/', views.SalirListaView.as_view(), name='salir_espera'),
    path('lista-de-espera/<int:pk>/confirmar/', views.ConfirmarCupoView.as_view(), name='confirmar_cupo'),
]
