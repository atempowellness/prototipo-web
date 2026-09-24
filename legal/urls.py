from django.urls import path

from . import views

urlpatterns = [
    path('privacidad/', views.PrivacidadView.as_view(), name='privacidad'),
    path('terminos/', views.TerminosView.as_view(), name='terminos'),
    path('libro-de-reclamaciones/', views.LibroView.as_view(), name='reclamaciones'),
    path('libro-de-reclamaciones/<int:pk>/quitar/', views.QuitarReclamacionView.as_view(), name='quitar_reclamacion'),
]
