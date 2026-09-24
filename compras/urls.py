from django.urls import path

from . import views

urlpatterns = [
    path('paquetes/<slug:slug>/comprar/', views.ComprarView.as_view(), name='comprar'),
    path('cuenta/compras/<int:pk>/', views.CompraView.as_view(), name='compra'),
]
