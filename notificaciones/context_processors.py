"""Entrega a todas las páginas las notificaciones de la campanita."""
from .avisos import (revisar_aperturas, revisar_recordatorios, revisar_recordatorios_de_citas,
                     revisar_recordatorios_de_encuentros, revisar_vencimientos)
from .models import MAXIMO_EN_MENU


def campanita(request):
    if request.path.startswith('/admin/'):
        return {}
    # Plazos de la lista de espera (en el prototipo se revisan al cargar cualquier página)
    from clases.lista_espera import revisar_listas_de_espera
    revisar_listas_de_espera()

    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    revisar_vencimientos(usuario)
    revisar_recordatorios(usuario)
    revisar_recordatorios_de_citas(usuario)
    revisar_recordatorios_de_encuentros(usuario)
    revisar_aperturas(usuario)
    return {
        'notificaciones': list(usuario.notificaciones.all()[:MAXIMO_EN_MENU]),
        'notificaciones_sin_leer': usuario.notificaciones.filter(leida=False).count(),
    }
