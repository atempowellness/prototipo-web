from django.urls import path

from . import views

urlpatterns = [
    path('paquetes/', views.PaquetesView.as_view(), name='paquetes'),
]
