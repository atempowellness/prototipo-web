"""
Registro de asistencia a clases, en un solo lugar.

- En el counter, la socia muestra su DNI. Recepción la busca en el panel ("Asistencia de hoy"),
  ve si su reserva sigue activa y marca "Asistió". Se puede marcar o corregir durante el día
  de la clase.
- Cuando la clase termina, las reservas no marcadas quedan como "No asistió" solas.
- Tras INASISTENCIAS_PARA_AVISO inasistencias en un mes, la socia recibe un aviso amable
  (una sola vez por mes).
- En el prototipo, "al terminar la clase" se revisa al cargar cualquier página; en la versión
  real sería una tarea automática.
"""
import datetime
from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from .models import DURACION_MINUTOS, Clase, Reserva
from .servicios import FRANJAS, franja_de

INASISTENCIAS_PARA_AVISO = 3
PERIODOS_RESUMEN = [7, 30, 90]   # días


class NoSePuedeMarcar(Exception):
    """Motivo por el que no se pudo marcar la asistencia."""


def _fin_de_clase_antes_de(momento):
    """Clases que ya terminaron en ese momento."""
    return momento - datetime.timedelta(minutes=DURACION_MINUTOS)


def revisar_asistencia():
    """Las reservas de clases terminadas que nadie marcó pasan a "No asistió" (y se revisan los avisos)."""
    pendientes = Reserva.objects.filter(cancelada=False, asistencia=Reserva.POR_REGISTRAR,
                                        clase__inicio__lte=_fin_de_clase_antes_de(timezone.now()))
    usuarias = set(pendientes.values_list('usuario_id', flat=True))
    if not usuarias:
        return
    pendientes.update(asistencia=Reserva.NO_ASISTIO)
    from django.contrib.auth import get_user_model
    for usuaria in get_user_model().objects.filter(pk__in=usuarias):
        revisar_inasistencias(usuaria)


def inasistencias_del_mes(usuaria):
    hoy = timezone.localdate()
    return usuaria.reservas.filter(cancelada=False, asistencia=Reserva.NO_ASISTIO,
                                   clase__inicio__year=hoy.year, clase__inicio__month=hoy.month).count()


def revisar_inasistencias(usuaria):
    """Aviso amable al llegar a 3 inasistencias en el mes (una sola vez por mes)."""
    from notificaciones import avisos
    from notificaciones.models import Notificacion

    hoy = timezone.localdate()
    ya_avisada = usuaria.notificaciones.filter(tipo=Notificacion.INASISTENCIAS, creada__year=hoy.year,
                                               creada__month=hoy.month).exists()
    if not ya_avisada and inasistencias_del_mes(usuaria) >= INASISTENCIAS_PARA_AVISO:
        avisos.inasistencias(usuaria)


def se_puede_marcar(reserva):
    """Solo reservas activas, y solo el mismo día de la clase."""
    return not reserva.cancelada and reserva.clase.fecha == timezone.localdate()


def marcar(reserva, asistio=True):
    if not se_puede_marcar(reserva):
        raise NoSePuedeMarcar('Solo se puede marcar la asistencia de reservas activas del día de hoy.')
    if asistio:
        reserva.asistencia, reserva.asistencia_marcada_en = Reserva.ASISTIO, timezone.now()
    else:
        # Desmarcar: vuelve a "por registrar" o, si la clase ya terminó, a "No asistió"
        terminada = reserva.clase.inicio <= _fin_de_clase_antes_de(timezone.now())
        reserva.asistencia = Reserva.NO_ASISTIO if terminada else Reserva.POR_REGISTRAR
        reserva.asistencia_marcada_en = None
    reserva.save(update_fields=['asistencia', 'asistencia_marcada_en'])
    if not asistio:
        revisar_inasistencias(reserva.usuario)


# --- Asistencia de hoy ---

def clases_de_hoy():
    """Las clases de hoy con sus reservas activas, en orden de hora."""
    hoy = timezone.localdate()
    clases = (Clase.objects.filter(inicio__date=hoy, cancelada=False)
              .select_related('sala', 'disciplina', 'instructor').order_by('inicio', 'sala__orden'))
    resultado = []
    for clase in clases:
        reservas = list(clase.reservas.filter(cancelada=False).select_related('usuario').order_by('usuario__nombre'))
        if reservas:
            resultado.append({'clase': clase, 'reservas': reservas,
                              'asistieron': sum(r.asistencia == Reserva.ASISTIO for r in reservas)})
    return resultado


def buscar_reservas_de_hoy(texto):
    """Reservas de hoy (activas y canceladas) de quien tenga ese DNI, o cuyo nombre o apellido coincida."""
    texto = (texto or '').strip()
    if not texto:
        return []
    hoy = timezone.localdate()
    filtro = Q(usuario__dni=texto) if texto.isdigit() else (
        Q(usuario__nombre__icontains=texto) | Q(usuario__apellido__icontains=texto))
    return list(Reserva.objects.filter(filtro, clase__inicio__date=hoy)
                .select_related('usuario', 'clase__sala', 'clase__disciplina').order_by('clase__inicio'))


# --- Resumen ---

def _porcentaje(parte, total):
    return round(100 * parte / total) if total else None


def resumen(dias):
    """Ocupación y asistencia de las clases terminadas en los últimos `dias` días (sin clases antiguas sin registro)."""
    ahora = timezone.now()
    desde = ahora - datetime.timedelta(days=dias)
    clases = list(Clase.objects.filter(inicio__gte=desde, inicio__lte=_fin_de_clase_antes_de(ahora), cancelada=False)
                  .exclude(reservas__asistencia=Reserva.SIN_REGISTRO)   # anteriores al control de asistencia
                  .select_related('sala', 'disciplina').distinct())
    reservas = list(Reserva.objects.filter(clase__in=clases, cancelada=False)
                    .exclude(asistencia=Reserva.SIN_REGISTRO).select_related('usuario'))
    por_clase = defaultdict(lambda: [0, 0])          # clase_id -> [reservas, asistencias]
    for r in reservas:
        por_clase[r.clase_id][0] += 1
        por_clase[r.clase_id][1] += r.asistencia == Reserva.ASISTIO

    def agrupar(clave, orden):
        grupos = defaultdict(lambda: {'clases': 0, 'capacidad': 0, 'reservas': 0, 'asistencias': 0})
        for c in clases:
            g = grupos[clave(c)]
            g['clases'] += 1
            g['capacidad'] += c.aforo
            g['reservas'] += por_clase[c.pk][0]
            g['asistencias'] += por_clase[c.pk][1]
        filas = []
        for nombre in orden:
            if nombre in grupos:
                g = grupos[nombre]
                g.update(nombre=nombre, inasistencias=g['reservas'] - g['asistencias'],
                         ocupacion=_porcentaje(g['asistencias'], g['capacidad']),
                         ocupacion_reservada=_porcentaje(g['reservas'], g['capacidad']),
                         asistencia=_porcentaje(g['asistencias'], g['reservas']))
                filas.append(g)
        return filas

    nombres_franja = dict((clave, nombre) for clave, nombre, _, _ in FRANJAS)
    disciplinas = sorted({c.disciplina for c in clases}, key=lambda d: d.orden)
    salas = sorted({c.sala for c in clases}, key=lambda s: s.orden)
    total = agrupar(lambda c: 'Total', ['Total'])

    faltas = defaultdict(int)
    for r in reservas:
        if r.asistencia == Reserva.NO_ASISTIO:
            faltas[r.usuario] += 1
    mas_faltas = sorted(faltas.items(), key=lambda x: (-x[1], x[0].nombre))[:10]

    return {
        'total': total[0] if total else None,
        'por_disciplina': agrupar(lambda c: c.disciplina.nombre, [d.nombre for d in disciplinas]),
        'por_franja': agrupar(lambda c: nombres_franja[franja_de(c.inicio)], [n for _, n, _, _ in FRANJAS]),
        'por_sala': agrupar(lambda c: c.sala.nombre, [s.nombre for s in salas]),
        'mas_faltas': mas_faltas,
    }
