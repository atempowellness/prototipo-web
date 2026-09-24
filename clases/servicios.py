"""
Reglas de clases y reservas, en un solo lugar.

- Las clases se crean solas a partir del horario base, para los próximos días.
- Reservar: con sesión, con un punto vigente el día de la clase, sin repetir la clase
  ni reservar dos a la misma hora, con cupo, y como máximo DIAS_PARA_RESERVAR días antes.
- Cancelar: con 12 horas o más de anticipación se devuelve el punto; con menos, se libera
  el cupo pero el punto no vuelve. Si el estudio cancela una clase, siempre se devuelve.
"""
import datetime

from django.db import transaction
from django.utils import timezone

from compras.models import Compra, compra_para_usar, devolver_credito, usar_credito

from .models import (DIAS_PARA_RESERVAR, Clase, HorarioBase, Reserva, numero_simulado)

FRANJAS = [
    ('temprano', 'Temprano (antes de 9:00)', 0, 9),
    ('manana', 'Mañana (9:00 a 12:00)', 9, 12),
    ('tarde', 'Tarde (12:00 a 18:00)', 12, 18),
    ('noche', 'Noche (desde 18:00)', 18, 24),
]


class NoSePuedeReservar(Exception):
    """Motivo por el que no se pudo reservar, con un texto para mostrar a la clienta."""


def dias_disponibles():
    hoy = timezone.localdate()
    return [hoy + datetime.timedelta(days=n) for n in range(DIAS_PARA_RESERVAR + 1)]


def generar_clases(hasta=None):
    """Crea (si faltan) las clases desde hoy hasta `hasta`, según el horario base activo."""
    hoy = timezone.localdate()
    hasta = hasta or hoy + datetime.timedelta(days=DIAS_PARA_RESERVAR)
    base = list(HorarioBase.objects.filter(activo=True).select_related('sala', 'disciplina', 'instructor'))
    zona = timezone.get_current_timezone()
    creadas = 0
    dia = hoy
    while dia <= hasta:
        for h in base:
            if h.dia_semana != dia.weekday():
                continue
            inicio = timezone.make_aware(datetime.datetime.combine(dia, h.hora), zona)
            _, nueva = Clase.objects.get_or_create(
                inicio=inicio, sala=h.sala,
                defaults={'disciplina': h.disciplina, 'instructor': h.instructor, 'nivel': h.nivel,
                          'ocupacion_simulada': numero_simulado()},
            )
            creadas += nueva
        dia += datetime.timedelta(days=1)
    return creadas


def franja_de(momento):
    hora = timezone.localtime(momento).hour
    for clave, _, desde, hasta in FRANJAS:
        if desde <= hora < hasta:
            return clave
    return 'noche'


def clases_del_dia(dia, disciplina=None, franja=None):
    zona = timezone.get_current_timezone()
    desde = timezone.make_aware(datetime.datetime.combine(dia, datetime.time.min), zona)
    clases = (Clase.objects.filter(inicio__gte=desde, inicio__lt=desde + datetime.timedelta(days=1))
              .select_related('sala', 'disciplina', 'instructor'))
    if disciplina:
        clases = clases.filter(disciplina__slug=disciplina)
    clases = list(clases)
    if franja:
        clases = [c for c in clases if franja_de(c.inicio) == franja]
    return clases


def reserva_activa(usuario, clase):
    if not usuario.is_authenticated:
        return None
    return clase.reservas.filter(usuario=usuario, cancelada=False).first()


def motivo_para_no_reservar(usuario, clase, simular=False):
    """Devuelve el texto de por qué no se puede reservar, o None si se puede."""
    if clase.cancelada:
        return 'Esta clase fue cancelada por el estudio.'
    if clase.empezo:
        return 'Esta clase ya empezó.'
    if clase.fecha > timezone.localdate() + datetime.timedelta(days=DIAS_PARA_RESERVAR):
        return f'Puedes reservar con hasta {DIAS_PARA_RESERVAR} días de anticipación.'
    if reserva_activa(usuario, clase):
        return 'Ya tienes una reserva en esta clase.'
    if Reserva.objects.filter(usuario=usuario, cancelada=False, clase__inicio=clase.inicio).exists():
        return 'Ya tienes otra clase reservada a esa misma hora.'
    if clase.cupos(simular) <= 0:
        return 'Esta clase está llena.'
    if compra_para_usar(usuario, clase.fecha) is None:
        return 'SIN_CREDITOS'
    return None


def reservar(usuario, clase, simular=False):
    with transaction.atomic():
        clase = Clase.objects.select_for_update().get(pk=clase.pk)
        motivo = motivo_para_no_reservar(usuario, clase, simular)
        if motivo:
            raise NoSePuedeReservar(motivo)
        compra = usar_credito(usuario, clase.fecha)
        return Reserva.objects.create(usuario=usuario, clase=clase, compra=compra)


def cancelar_reserva(reserva, por_el_estudio=False):
    """
    Cancela una reserva. Devuelve True si el punto se devolvió.
    Si la cancela el estudio (desde el panel), siempre se devuelve y se avisa a la clienta.
    """
    if reserva.cancelada or (reserva.clase.empezo and not por_el_estudio):
        return False
    compra = Compra.objects.filter(pk=reserva.compra_id).first()   # dato actualizado
    devuelto = (por_el_estudio or reserva.se_devuelve_si_cancela) and devolver_credito(compra)
    reserva.cancelada = True
    reserva.cancelada_en = timezone.now()
    reserva.credito_devuelto = devuelto
    reserva.save(update_fields=['cancelada', 'cancelada_en', 'credito_devuelto'])
    if por_el_estudio:
        from notificaciones import avisos
        avisos.reserva_cancelada_por_estudio(reserva, devuelto)
    # El cupo liberado pasa primero a la lista de espera (si hay)
    from .lista_espera import procesar_lista
    procesar_lista(reserva.clase)
    return devuelto


def cancelar_clase_por_estudio(clase, motivo=''):
    """El estudio cancela una clase: todas las reservas recuperan su punto y se les avisa."""
    from notificaciones import avisos

    if clase.cancelada:
        return 0
    clase.cancelada = True
    clase.motivo_cancelacion = motivo
    clase.save(update_fields=['cancelada', 'motivo_cancelacion'])
    afectadas = 0
    for reserva in clase.reservas_activas().select_related('usuario', 'compra'):
        devuelto = devolver_credito(reserva.compra)
        reserva.cancelada = True
        reserva.cancelada_en = timezone.now()
        reserva.credito_devuelto = devuelto
        reserva.save(update_fields=['cancelada', 'cancelada_en', 'credito_devuelto'])
        avisos.clase_cancelada(reserva, devuelto)
        afectadas += 1
    from .lista_espera import procesar_lista
    procesar_lista(clase)   # cierra la lista de espera y avisa a quienes esperaban
    return afectadas


def proximas_reservas(usuario):
    return (usuario.reservas.filter(cancelada=False, clase__inicio__gte=timezone.now() - datetime.timedelta(minutes=50))
            .select_related('clase__sala', 'clase__disciplina', 'clase__instructor'))
