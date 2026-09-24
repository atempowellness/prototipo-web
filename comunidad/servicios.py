"""
Reglas de los encuentros de Atempo Circle, en un solo lugar.

- Acceso: una compra que incluya Atempo Circle (desde Atempo 5) y siga vigente el día del
  encuentro. Cuenta la fecha de vencimiento, no los puntos que queden: los encuentros no
  gastan puntos.
- Apertura escalonada: la inscripción se abre tantos días antes del encuentro como diga el
  paquete (panel → Paquetes → "inscripción a encuentros"). Si tiene varios, cuenta el que
  abre antes. En pantalla solo se muestra su fecha, sin comparar con otros paquetes.
- Cancelar: hasta que empiece el encuentro. Si el estudio lo cancela, se avisa a todas.
- Encuentros de ejemplo: se vuelven a crear solos cuando pasan (RENOVAR_EJEMPLOS).
"""
import datetime

from django.db import transaction
from django.utils import timezone

from .models import CAFE, CHARLA, SALIDA, TALLER, AvisoDeApertura, Encuentro, Inscripcion

CUPOS_POCOS = 3            # desde cuántos cupos se muestra "Quedan X cupos" (el cupo no se muestra)
ENCUENTROS_EN_INICIO = 3
RENOVAR_EJEMPLOS = True    # en la versión real, el estudio crea los encuentros en el panel

# Encuentros de ejemplo (del prototipo HTML). `dias`: a cuántos días de hoy, como mínimo, se crea
# el siguiente (luego se corre hasta su día de la semana). El coffee queda a 1-7 días, así siempre
# hay uno abierto para todos los paquetes; los demás muestran la apertura escalonada.
EJEMPLOS = [
    {'clave': 'coffee', 'titulo': 'Coffee morning de bienvenida', 'tipo': CAFE, 'dia_semana': 5,
     'hora': datetime.time(11, 0), 'dias': 1, 'lugar': 'Zona social de Atempo', 'cupo': 20,
     'descripcion': 'Conoce a otras socias y al equipo de instructores con un café de especialidad.'},
    {'clave': 'charla', 'titulo': 'Charla: fuerza y salud hormonal', 'tipo': CHARLA, 'dia_semana': 3,
     'hora': datetime.time(19, 15), 'dias': 6, 'lugar': 'Sala Calma', 'cupo': 24,
     'descripcion': 'Con Lic. María Becerra, nutricionista del equipo. Qué cambia en esta etapa y cómo '
                    'el entrenamiento de fuerza te ayuda.'},
    {'clave': 'caminata', 'titulo': 'Caminata por el Malecón de Miraflores', 'tipo': SALIDA, 'dia_semana': 6,
     'hora': datetime.time(8, 0), 'dias': 12, 'lugar': 'Punto de encuentro: Parque del Amor', 'cupo': 25,
     'descripcion': 'Recorrido suave de 5 km y desayuno saludable al final.'},
    {'clave': 'skincare', 'titulo': 'Taller de skincare y autocuidado', 'tipo': TALLER, 'dia_semana': 4,
     'hora': datetime.time(18, 30), 'dias': 18, 'lugar': 'Zona social de Atempo', 'cupo': 16,
     'descripcion': 'Rutinas simples de cuidado de la piel con una dermatóloga invitada.'},
    {'clave': 'brunch', 'titulo': 'Brunch saludable de fin de mes', 'tipo': CAFE, 'dia_semana': 5,
     'hora': datetime.time(10, 30), 'dias': 25, 'lugar': 'Café aliado en San Isidro', 'cupo': 30,
     'descripcion': 'Recetas nutritivas y buena conversación para cerrar el mes juntas.'},
]


class NoSePuedeInscribir(Exception):
    """Motivo por el que no se pudo inscribir, con un texto para mostrar a la socia."""


def asegurar_encuentros_de_ejemplo():
    """Crea el siguiente encuentro de cada ejemplo si el anterior ya pasó (o nunca existió)."""
    if not RENOVAR_EJEMPLOS:
        return
    ahora = timezone.now()
    hoy = timezone.localdate()
    zona = timezone.get_current_timezone()
    for ejemplo in EJEMPLOS:
        if Encuentro.objects.filter(clave_ejemplo=ejemplo['clave'], inicio__gt=ahora).exists():
            continue
        dia = hoy + datetime.timedelta(days=ejemplo['dias'])
        dia += datetime.timedelta(days=(ejemplo['dia_semana'] - dia.weekday()) % 7)
        Encuentro.objects.create(
            clave_ejemplo=ejemplo['clave'], titulo=ejemplo['titulo'], tipo=ejemplo['tipo'],
            inicio=timezone.make_aware(datetime.datetime.combine(dia, ejemplo['hora']), zona),
            lugar=ejemplo['lugar'], descripcion=ejemplo['descripcion'], cupo=ejemplo['cupo'],
        )


def proximos_encuentros(tipo=None):
    encuentros = Encuentro.objects.filter(inicio__gt=timezone.now())
    if tipo:
        encuentros = encuentros.filter(tipo=tipo)
    return encuentros


# --- Acceso y apertura ---

def compras_con_circle(usuario, dia):
    """Compras que incluyen Atempo Circle y siguen vigentes el día `dia` (aunque no queden puntos)."""
    dia = max(dia, timezone.localdate())
    return usuario.compras.filter(incluye_circle=True, vence__gte=dia).select_related('paquete')


def dias_de_anticipacion(usuario, encuentro):
    """Con cuántos días de anticipación se abre su inscripción, o None si no tiene acceso."""
    compras = list(compras_con_circle(usuario, encuentro.fecha))
    if not compras:
        return None
    return max((c.paquete.dias_inscripcion_circle or 0) if c.paquete else 0 for c in compras)


def apertura_para(usuario, encuentro):
    """El día en que se abre su inscripción (desde las 00:00), o None si no tiene acceso."""
    dias = dias_de_anticipacion(usuario, encuentro)
    if dias is None:
        return None
    return encuentro.fecha - datetime.timedelta(days=dias)


def inscripcion_activa(usuario, encuentro):
    if not usuario.is_authenticated:
        return None
    return encuentro.inscripciones.filter(usuario=usuario, cancelada=False).first()


def motivo_para_no_inscribirse(usuario, encuentro):
    """Devuelve el texto de por qué no se puede inscribir, o None si se puede."""
    if encuentro.cancelado:
        return 'Este encuentro fue cancelado por el estudio.'
    if encuentro.empezo:
        return 'Este encuentro ya empezó.'
    if inscripcion_activa(usuario, encuentro):
        return 'Ya estás inscrita en este encuentro.'
    if encuentro.cupos() <= 0:
        return 'Este encuentro está lleno.'
    apertura = apertura_para(usuario, encuentro)
    if apertura is None:
        return 'SIN_ACCESO'
    if timezone.localdate() < apertura:
        return 'AUN_NO'
    return None


def vence_antes_del_encuentro(usuario, encuentro):
    """Si tiene Atempo Circle hoy, pero su paquete vence antes del encuentro: la fecha en que vence."""
    hoy = timezone.localdate()
    ultima = usuario.compras.filter(incluye_circle=True, vence__gte=hoy).order_by('-vence').first()
    if ultima and ultima.vence < encuentro.fecha:
        return ultima.vence
    return None


def estado_de_encuentro(encuentro, usuario):
    """Todo lo que la tarjeta de un encuentro necesita mostrar."""
    cupos = encuentro.cupos()
    estado = {
        'encuentro': encuentro,
        'mi_inscripcion': inscripcion_activa(usuario, encuentro),
        'lleno': cupos <= 0,
        'pocos_cupos': 0 < cupos <= CUPOS_POCOS,
        'cupos': cupos,
        'apertura': None,
        'pidio_aviso': False,
    }
    if usuario.is_authenticated and not estado['mi_inscripcion']:
        apertura = apertura_para(usuario, encuentro)
        if apertura and timezone.localdate() < apertura:
            estado['apertura'] = apertura
            estado['pidio_aviso'] = encuentro.avisos_de_apertura.filter(usuario=usuario).exists()
    return estado


# --- Inscribirse y cancelar ---

def inscribir(usuario, encuentro):
    with transaction.atomic():
        encuentro = Encuentro.objects.select_for_update().get(pk=encuentro.pk)
        motivo = motivo_para_no_inscribirse(usuario, encuentro)
        if motivo:
            raise NoSePuedeInscribir(motivo)
        inscripcion = Inscripcion.objects.create(usuario=usuario, encuentro=encuentro)
    AvisoDeApertura.objects.filter(usuario=usuario, encuentro=encuentro).delete()
    return inscripcion


def cancelar_inscripcion(inscripcion, por_el_estudio=False):
    if inscripcion.cancelada or (inscripcion.encuentro.empezo and not por_el_estudio):
        return False
    inscripcion.cancelada = True
    inscripcion.cancelada_en = timezone.now()
    inscripcion.save(update_fields=['cancelada', 'cancelada_en'])
    if por_el_estudio:
        from notificaciones import avisos
        avisos.inscripcion_cancelada_por_estudio(inscripcion)
    return True


def cancelar_encuentro_por_estudio(encuentro):
    """El estudio cancela un encuentro: se avisa a todas las inscritas."""
    from notificaciones import avisos

    if encuentro.cancelado:
        return 0
    encuentro.cancelado = True
    encuentro.save(update_fields=['cancelado'])
    afectadas = 0
    for inscripcion in encuentro.inscripciones_activas().select_related('usuario'):
        inscripcion.cancelada = True
        inscripcion.cancelada_en = timezone.now()
        inscripcion.save(update_fields=['cancelada', 'cancelada_en'])
        avisos.encuentro_cancelado(inscripcion)
        afectadas += 1
    encuentro.avisos_de_apertura.all().delete()
    return afectadas


def pedir_o_quitar_aviso(usuario, encuentro):
    """"Recordarme": lo activa o, si ya estaba, lo quita. Devuelve True si quedó activo."""
    aviso, creado = AvisoDeApertura.objects.get_or_create(usuario=usuario, encuentro=encuentro)
    if not creado:
        aviso.delete()
    return creado


def aperturas_avisadas(usuario):
    """
    Encuentros cuya inscripción ya se abrió y de la que se le avisó ("Recordarme"), mientras
    no se haya apuntado y el encuentro no haya pasado. Se muestran arriba de Comunidad con el
    correo simulado. (Al apuntarse, el pedido de aviso se borra.)
    """
    return (usuario.avisos_de_apertura.filter(avisado=True, encuentro__cancelado=False,
                                              encuentro__inicio__gt=timezone.now())
            .select_related('encuentro').order_by('encuentro__inicio'))


def proximas_inscripciones(usuario):
    return (usuario.inscripciones.filter(cancelada=False, encuentro__inicio__gte=timezone.now()
                                         - datetime.timedelta(hours=2))
            .select_related('encuentro'))
