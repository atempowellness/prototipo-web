"""
Programa de referidas ("Trae a una amiga").

Reglas acordadas:
- Cada cuenta puede usar un solo código de referida en toda su historia (ni el suyo propio).
- El beneficio se activa con la primera compra de un paquete desde Atempo 5
  (aunque antes haya comprado Atempo 1 para probar).
- La amiga nueva recibe 1 crédito de regalo con la misma vigencia de esa compra.
- Quien invitó recibe 1 crédito de regalo válido por 1 mes desde ese día,
  con un tope de 5 por mes calendario. Si llegó al tope, la amiga igual recibe el suyo.
- Los códigos no distinguen mayúsculas de minúsculas.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Compra, sumar_meses

CREDITOS_MINIMOS = 5          # "desde Atempo 5"
TOPE_MENSUAL = 5
VIGENCIA_REGALO_MESES = 1


def buscar_por_codigo(codigo):
    """Devuelve la cuenta dueña del código (sin importar mayúsculas) o None."""
    codigo = (codigo or '').strip()
    if not codigo:
        return None
    return get_user_model().objects.filter(codigo_referida__iexact=codigo).first()


def paquete_califica(paquete):
    return paquete is not None and paquete.creditos >= CREDITOS_MINIMOS


def ya_tuvo_compra_que_califica(usuario, excepto=None):
    compras = usuario.compras.filter(tipo=Compra.COMPRA, creditos__gte=CREDITOS_MINIMOS)
    if excepto is not None:
        compras = compras.exclude(pk=excepto.pk)
    return compras.exists()


def puede_ingresar_codigo_al_pagar(usuario, paquete):
    """El campo del código solo aparece si esta compra puede activar el beneficio."""
    return (usuario.referida_por_id is None and paquete_califica(paquete)
            and not ya_tuvo_compra_que_califica(usuario))


def activara_beneficio(usuario, paquete):
    """Ya tiene un código (del registro) y esta compra lo activará."""
    return (usuario.referida_por_id is not None and paquete_califica(paquete)
            and not ya_tuvo_compra_que_califica(usuario))


def regalos_del_mes(invitadora):
    hoy = timezone.localdate()
    return invitadora.compras.filter(tipo=Compra.REGALO, referida__isnull=False,
                                     fecha__year=hoy.year, fecha__month=hoy.month).exclude(referida=invitadora)


def _regalo(usuario, vence, referida):
    return Compra.objects.create(
        tipo=Compra.REGALO, usuario=usuario, referida=referida, vence=vence,
        nombre_paquete='Crédito de regalo por referida', creditos=1, precio_pagado=0,
    )


def aplicar_beneficio(compra):
    """
    Se llama después de registrar una compra pagada. Si corresponde, entrega los
    créditos de regalo. Devuelve un dict con lo que pasó (para los mensajes) o None.
    """
    usuaria = compra.usuario
    invitadora = usuaria.referida_por
    if invitadora is None or not paquete_califica(compra.paquete):
        return None
    if ya_tuvo_compra_que_califica(usuaria, excepto=compra):
        return None

    with transaction.atomic():
        # Crédito de la amiga nueva: con la misma vigencia de su compra
        _regalo(usuaria, compra.vence, referida=usuaria)
        # Crédito de quien invitó: 1 mes desde hoy, con tope mensual
        invitadora_recibe = regalos_del_mes(invitadora).count() < TOPE_MENSUAL
        if invitadora_recibe:
            _regalo(invitadora, sumar_meses(timezone.localdate(), VIGENCIA_REGALO_MESES), referida=usuaria)
    return {'invitadora': invitadora, 'invitadora_recibe': invitadora_recibe}


def estado_de_invitadas(invitadora):
    """Lista para Mi cuenta: cada amiga invitada y si ya activó el beneficio."""
    regalos = {r.referida_id: r for r in invitadora.compras.filter(tipo=Compra.REGALO).exclude(referida=invitadora)}
    lista = []
    for amiga in invitadora.invitadas.order_by('-date_joined'):
        activo = ya_tuvo_compra_que_califica(amiga)
        lista.append({
            'nombre': amiga.nombre_corto,
            'compro': activo,
            'recibi_credito': amiga.pk in regalos,
        })
    return lista
