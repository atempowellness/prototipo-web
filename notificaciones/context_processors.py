"""Entrega a todas las páginas las notificaciones de la campanita."""
from .avisos import revisar_recordatorios, revisar_vencimientos
from .models import MAXIMO_EN_MENU


def campanita(request):
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated or request.path.startswith('/admin/'):
        return {}
    revisar_vencimientos(usuario)
    revisar_recordatorios(usuario)
    return {
        'notificaciones': list(usuario.notificaciones.all()[:MAXIMO_EN_MENU]),
        'notificaciones_sin_leer': usuario.notificaciones.filter(leida=False).count(),
    }
