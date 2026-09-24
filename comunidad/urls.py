from django.urls import path

from . import views

urlpatterns = [
    path('comunidad/', views.ComunidadView.as_view(), name='comunidad'),
    path('comunidad/<int:pk>/apuntarme/', views.InscribirseView.as_view(), name='inscribirse'),
    path('comunidad/<int:pk>/recordarme/', views.RecordarmeView.as_view(), name='recordarme'),
    path('comunidad/asistencia/<int:pk>/cancelar/', views.CancelarInscripcionView.as_view(),
         name='cancelar_inscripcion'),
]
