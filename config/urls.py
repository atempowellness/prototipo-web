"""
Direcciones principales del sitio.

Cada app de Atempo define sus propias direcciones en su archivo urls.py
y aquí solo se "enchufan".
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]
