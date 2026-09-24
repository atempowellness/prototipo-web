from django.urls import path

from . import views

urlpatterns = [
    path('notificaciones/leidas/', views.marcar_leidas, name='notificaciones_leidas'),
    path('notificaciones/<int:pk>/borrar/', views.borrar, name='notificacion_borrar'),
    path('notificaciones/borrar-todas/', views.borrar_todas, name='notificaciones_borrar_todas'),
]
