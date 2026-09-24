"""
Reglas de nutrición y masajes, en un solo lugar.

Cómo se paga una cita (según la tesis):
1. Primero, una sesión incluida en un paquete vigente el día de la cita (la del que vence antes).
   Nutrición viene incluida desde Atempo 5; masajes, en Atempo 20 y 40.
2. Si no le quedan incluidas, una sesión adicional con créditos, solo si tiene un paquete vigente
   que la habilite: nutrición 1 crédito (desde Atempo 10), masaje 2 créditos (desde Atempo 20).
Cancelar con 12 horas o más devuelve la sesión o los créditos; con menos, no.
"""
import datetime
from dataclasses import dataclass

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from clases.models import DIAS_PARA_RESERVAR, Profesional
from compras.models import Compra, devolver_credito, usar_credito
from paquetes.models import Paquete

from .models import MASAJES, NUTRICION, Cita, HorarioAtencion

CAMPO_INCLUIDAS = {NUTRICION: ('sesiones_nutricion', 'nutricion_usada'),
                   MASAJES: ('sesiones_masaje', 'masaje_usado')}
CAMPO_COSTO = {NUTRICION: 'costo_nutricion_adicional', MASAJES: 'costo_masaje_adicional'}
PASO_MINUTOS = 60          # las horas de inicio van de hora en hora dentro de cada bloque


class NoSePuedeAgendar(Exception):
    pass


@dataclass
class Plan:
    """Cómo se pagaría una cita: 'incluida', 'creditos', 'sin_creditos' o 'no_habilitado'."""
    modo: str
    compra: Compra = None
    costo: int = 0
    paquete_minimo: str = ''


def _vigentes_ese_dia(usuario, fecha):
    dia = max(fecha, timezone.localdate())
    return usuario.compras.filter(vence__gte=dia)


def sesiones_incluidas_disponibles(usuario, servicio, fecha=None):
    total, usadas = CAMPO_INCLUIDAS[servicio]
    compras = _vigentes_ese_dia(usuario, fecha or timezone.localdate())
    return sum(getattr(c, total) - getattr(c, usadas) for c in compras)


def paquete_minimo_para_adicional(servicio):
    filtro = {f'{CAMPO_COSTO[servicio]}__isnull': False, 'activo': True}
    paquete = Paquete.objects.filter(**filtro).order_by('creditos').first()
    return paquete.nombre if paquete else ''


def plan_de_pago(usuario, servicio, fecha):
    total, usadas = CAMPO_INCLUIDAS[servicio]
    compras = _vigentes_ese_dia(usuario, fecha)
    incluida = (compras.filter(**{f'{usadas}__lt': F(total)}).order_by('vence', 'fecha').first())
    if incluida:
        return Plan('incluida', compra=incluida)

    costos = [getattr(c.paquete, CAMPO_COSTO[servicio]) for c in compras.filter(tipo=Compra.COMPRA)
              .select_related('paquete') if c.paquete and getattr(c.paquete, CAMPO_COSTO[servicio])]
    if not costos:
        return Plan('no_habilitado', paquete_minimo=paquete_minimo_para_adicional(servicio))
    costo = min(costos)
    disponibles = sum(c.creditos_disponibles for c in compras)
    return Plan('creditos' if disponibles >= costo else 'sin_creditos', costo=costo)


def dias_disponibles():
    hoy = timezone.localdate()
    return [hoy + datetime.timedelta(days=n) for n in range(DIAS_PARA_RESERVAR + 1)]


def profesionales_de(servicio):
    return Profesional.objects.filter(area=servicio, activo=True)


def _ocupada(usuario, profesional, inicio, fin):
    """¿Choca con otra cita de la profesional, o con una cita o clase de la clienta?"""
    choques = Cita.objects.filter(cancelada=False, inicio__lt=fin, fin__gt=inicio)
    if choques.filter(profesional=profesional).exists():
        return True
    if usuario is not None and usuario.is_authenticated:
        if choques.filter(usuario=usuario).exists():
            return True
        from clases.models import DURACION_MINUTOS
        desde = inicio - datetime.timedelta(minutes=DURACION_MINUTOS)
        if usuario.reservas.filter(cancelada=False, clase__inicio__gt=desde, clase__inicio__lt=fin).exists():
            return True
    return False


def horas_libres(servicio, tipo, dia, profesional=None, usuario=None):
    """Lista de (inicio, profesional) libres ese día para ese tipo de sesión."""
    zona = timezone.get_current_timezone()
    ahora = timezone.now()
    duracion = datetime.timedelta(minutes=tipo.duracion_minutos)
    profesionales = [profesional] if profesional else list(profesionales_de(servicio))
    libres = []
    for bloque in HorarioAtencion.objects.filter(profesional__in=profesionales, dia_semana=dia.weekday(), activo=True):
        inicio = timezone.make_aware(datetime.datetime.combine(dia, bloque.desde), zona)
        limite = timezone.make_aware(datetime.datetime.combine(dia, bloque.hasta), zona)
        while inicio + duracion <= limite:
            if inicio > ahora and not _ocupada(usuario, bloque.profesional, inicio, inicio + duracion):
                libres.append((inicio, bloque.profesional))
            inicio += datetime.timedelta(minutes=PASO_MINUTOS)
    libres.sort(key=lambda x: (x[0], x[1].orden))
    return libres


def agendar(usuario, profesional, tipo, inicio, ficha=None):
    """Crea la cita y descuenta la sesión incluida o los créditos."""
    fin = inicio + datetime.timedelta(minutes=tipo.duracion_minutos)
    fecha = timezone.localtime(inicio).date()
    if inicio <= timezone.now():
        raise NoSePuedeAgendar('Esa hora ya pasó. Elige otra.')
    if fecha > timezone.localdate() + datetime.timedelta(days=DIAS_PARA_RESERVAR):
        raise NoSePuedeAgendar(f'Puedes agendar con hasta {DIAS_PARA_RESERVAR} días de anticipación.')
    if (inicio, profesional) not in horas_libres(tipo.servicio, tipo, fecha, profesional, usuario):
        raise NoSePuedeAgendar('Esa hora ya no está disponible. Elige otra.')

    with transaction.atomic():
        plan = plan_de_pago(usuario, tipo.servicio, fecha)
        cita = Cita(usuario=usuario, profesional=profesional, tipo=tipo, inicio=inicio, fin=fin, **(ficha or {}))
        if plan.modo == 'incluida':
            _, usadas = CAMPO_INCLUIDAS[tipo.servicio]
            Compra.objects.filter(pk=plan.compra.pk).update(**{usadas: F(usadas) + 1})
            cita.forma, cita.compra = Cita.INCLUIDA, plan.compra
        elif plan.modo == 'creditos':
            usados = [usar_credito(usuario, fecha) for _ in range(plan.costo)]
            cita.forma, cita.compras_creditos = Cita.CREDITOS, [c.pk for c in usados if c]
        else:
            raise NoSePuedeAgendar('SIN_SESIONES')
        cita.save()
        return cita


def _devolver(cita):
    if cita.forma == Cita.INCLUIDA:
        _, usadas = CAMPO_INCLUIDAS[cita.servicio]
        compra = Compra.objects.filter(pk=cita.compra_id).first()   # dato actualizado, no una copia vieja
        if compra and compra.vigente and getattr(compra, usadas) > 0:
            Compra.objects.filter(pk=compra.pk).update(**{usadas: F(usadas) - 1})
            return True
        return False
    devueltos = [devolver_credito(Compra.objects.filter(pk=pk).first()) for pk in cita.compras_creditos]
    return any(devueltos)


def cancelar_cita(cita, por_el_estudio=False):
    """Cancela la cita. Devuelve True si se devolvió la sesión o los créditos."""
    if cita.cancelada or (cita.empezo and not por_el_estudio):
        return False
    devuelta = (por_el_estudio or cita.se_devuelve_si_cancela) and _devolver(cita)
    cita.cancelada, cita.cancelada_en, cita.devuelta = True, timezone.now(), devuelta
    cita.save(update_fields=['cancelada', 'cancelada_en', 'devuelta'])
    if por_el_estudio:
        from notificaciones import avisos
        avisos.cita_cancelada(cita, devuelta)
    return devuelta


def proximas_citas(usuario):
    return (usuario.citas.filter(cancelada=False, fin__gte=timezone.now())
            .select_related('profesional', 'tipo'))
