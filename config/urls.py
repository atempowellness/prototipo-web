"""
Direcciones principales del sitio.

Cada app de Atempo define sus propias direcciones en su archivo urls.py
y aquí solo se "enchufan".
"""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Administración de Atempo'
admin.site.site_title = 'Administración de Atempo'
admin.site.index_title = 'Panel de administración'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('paquetes.urls')),
    path('', include('cuentas.urls')),
    path('', include('compras.urls')),
    path('', include('notificaciones.urls')),
]
