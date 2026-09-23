"""
Mapa del sitio de Atempo Wellness.

Las páginas que aún no tienen contenido muestran solo su título y el
aviso "Página en construcción". El contenido de cada una se define
junto con el equipo antes de programarlo.
"""
from django.urls import path
from django.views.generic import TemplateView

from . import views


def en_construccion(titulo):
    """Página provisional que solo muestra su título."""
    return TemplateView.as_view(
        template_name='en_construccion.html',
        extra_context={'titulo': titulo},
    )


urlpatterns = [
    # Páginas públicas
    path('', views.InicioView.as_view(), name='inicio'),
    path('horarios/', en_construccion('Clases y horarios'), name='horarios'),
    path('paquetes/', en_construccion('Paquetes'), name='paquetes'),
    path('bienestar/', en_construccion('Nutrición y masajes'), name='bienestar'),
    path('comunidad/', en_construccion('Comunidad'), name='comunidad'),
    path('nosotros/', views.NosotrosView.as_view(), name='nosotros'),

    # Páginas de la clienta
    path('cuenta/', en_construccion('Mi cuenta'), name='cuenta'),
    path('cuenta/registro/', en_construccion('Crear cuenta'), name='registro'),
    path('cuenta/ingresar/', en_construccion('Iniciar sesión'), name='ingresar'),

    # Páginas legales
    path('privacidad/', en_construccion('Política de privacidad'), name='privacidad'),
    path('terminos/', en_construccion('Términos y condiciones'), name='terminos'),
    path('libro-de-reclamaciones/', en_construccion('Libro de reclamaciones'), name='reclamaciones'),
]
