"""
Mapa del sitio de Atempo Wellness: páginas generales. Cada app define las suyas
(paquetes, cuentas, clases, bienestar, comunidad, legal...).
"""
from django.urls import path

from . import views

urlpatterns = [
    # Páginas públicas
    path('', views.InicioView.as_view(), name='inicio'),
    path('nosotros/', views.NosotrosView.as_view(), name='nosotros'),
    # Comunidad está en la app "comunidad" y las páginas legales en la app "legal"
]
