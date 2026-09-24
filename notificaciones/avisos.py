"""
Textos de cada notificación, en un solo lugar para editarlos fácilmente.
"""
from django.urls import reverse
from django.utils.formats import date_format

from .models import Notificacion, notificar


def _fecha(dia):
    return date_format(dia, 'j \\d\\e F')


def creditos_activados(compra):
    """Después de pagar un paquete."""
    if compra.creditos == 1:
        texto = f'Se activó tu crédito de {compra.nombre_paquete}. Puedes usarlo hasta el {_fecha(compra.vence)}.'
    else:
        texto = (f'Se activaron tus {compra.creditos} créditos de {compra.nombre_paquete}. '
                 f'Puedes usarlos hasta el {_fecha(compra.vence)}.')
    notificar(compra.usuario, Notificacion.CREDITOS_ACTIVADOS, texto, reverse('cuenta'))


def credito_extra_activado(regalo, invitadora):
    """A la amiga nueva, cuando se activa su crédito extra por referida."""
    notificar(regalo.usuario, Notificacion.CREDITO_EXTRA,
              f'Se activó tu crédito extra por venir invitada por {invitadora.nombre}. '
              f'Puedes usarlo hasta el {_fecha(regalo.vence)}.',
              reverse('cuenta'))


def bienvenida(usuario):
    notificar(usuario, Notificacion.BIENVENIDA,
              f'¡Bienvenida a Atempo, {usuario.nombre}! Elige tu paquete y reserva tu primera clase.',
              reverse('paquetes'))


def amiga_se_registro(invitadora, amiga):
    notificar(invitadora, Notificacion.REFERIDA_REGISTRO,
              f'{amiga.nombre_corto} se registró con tu código. Cuando compre su primer paquete desde '
              f'Atempo 5, las dos reciben 1 crédito.',
              reverse('cuenta'))


def amiga_compro(invitadora, amiga, regalo):
    """A quien invitó. `regalo` es su crédito de regalo, o None si ya llegó al tope del mes."""
    if regalo is not None:
        texto = (f'¡{amiga.nombre_corto} compró su paquete con tu código! Se activó tu crédito de regalo: '
                 f'puedes usarlo hasta el {_fecha(regalo.vence)}.')
    else:
        texto = (f'{amiga.nombre_corto} compró su paquete con tu código. Este mes ya llegaste al tope '
                 f'de 5 créditos por referidas.')
    notificar(invitadora, Notificacion.REFERIDA_COMPRA, texto, reverse('cuenta'))


def revisar_vencimientos(usuario):
    """
    Crea el aviso de créditos por vencer (7 días o menos) una sola vez por compra.
    Se revisa al cargar cualquier página; en la versión real sería una tarea diaria.
    """
    from compras.models import compras_vigentes

    ya_avisadas = set(usuario.notificaciones.filter(tipo=Notificacion.VENCIMIENTO)
                      .values_list('compra_id', flat=True))
    for compra in compras_vigentes(usuario):
        if compra.vence_pronto and compra.pk not in ya_avisadas:
            origen = 'de regalo por referida' if compra.es_regalo else f'de tu {compra.nombre_paquete}'
            fecha = _fecha(compra.vence)
            if compra.creditos_disponibles == 1:
                texto = f'Te queda 1 crédito {origen} y vence el {fecha}. ¡Reserva tu clase!'
            else:
                texto = (f'Te quedan {compra.creditos_disponibles} créditos {origen} y vencen el {fecha}. '
                         f'¡Reserva tus clases!')
            notificar(usuario, Notificacion.VENCIMIENTO, texto, reverse('horarios'), compra=compra)
