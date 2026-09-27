from django.urls import path

from . import views

urlpatterns = [
    path('cuenta/', views.MiCuentaView.as_view(), name='cuenta'),
    path('cuenta/registro/', views.RegistroView.as_view(), name='registro'),
    path('cuenta/ingresar/', views.IngresarView.as_view(), name='ingresar'),
    path('cuenta/salir/', views.SalirView.as_view(), name='salir'),
    path('cuenta/demostracion/', views.DemostracionView.as_view(), name='demostracion'),
    path('cuenta/fundadora/agradecimiento/', views.MuroFundadorasView.as_view(), name='muro_fundadoras'),
    path('cuenta/recuperar/', views.RecuperarView.as_view(), name='recuperar'),
    path('cuenta/nueva-clave/<uidb64>/<token>/', views.NuevaClaveView.as_view(), name='nueva_clave'),
]
