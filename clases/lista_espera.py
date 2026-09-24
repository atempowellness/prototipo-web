"""
Lista de espera de las clases llenas, en un solo lugar.

- Anotarse: con un punto vigente el día de la clase (no se aparta: se cobra al confirmar),
  sin otra clase a la misma hora y en hasta MAXIMO_LISTAS listas a la vez.
- Cuando se libera un cupo, se guarda para la lista (nadie más lo ve libre) y se le ofrece a
  la primera que espera, con MINUTOS_PARA_CONFIRMAR para confirmar. Si no confirma, o ya no
  tiene punto, pasa a la siguiente.
- De noche (NOCHE_DESDE a NOCHE_HASTA) el plazo no corre.
- La lista se cierra HORAS_CIERRE antes de la clase: el plazo nunca pasa de ese cierre. Si al
  cerrar queda un cupo libre (o se libera de noche y la lista ya no alcanza a abrir), queda
  libre para cualquiera y se avisa a quienes esperaban.
- En el prototipo no hay un proceso de fondo: los plazos se revisan al cargar cualquier página
  (revisar_listas_de_espera). En la versión real sería una tarea automática.
"""
import datetime

from django.db import transaction
from django.utils import timezone

from compras.models import compra_para_usar, usar_credito

from .models import Clase, ListaEspera, Reserva

MINUTOS_PARA_CONFIRMAR = 45
HORAS_CIERRE = 2
MAXIMO_LISTAS = 3
NOCHE_DESDE = datetime.time(22, 0)
NOCHE_HASTA = datetime.time(5, 0)


class NoSePuedeAnotar(Exception):
    """Motivo por el que no se pudo usar la lista de espera, con un texto para mostrar."""


# --- Plazos ---

def cierre_de_lista(clase):
    return clase.inicio - datetime.timedelta(hours=HORAS_CIERRE)


def _de_noche(momento):
    hora = timezone.localtime(momento).time()
    return hora >= NOCHE_DESDE or hora < NOCHE_HASTA


def _siguiente_manana(momento):
    """Las 5:00 siguientes a un momento de la noche."""
    local = timezone.localtime(momento)
    dia = local.date() + datetime.timedelta(days=1) if local.time() >= NOCHE_DESDE else local.date()
    return timezone.make_aware(datetime.datetime.combine(dia, NOCHE_HASTA))


def inicio_del_plazo(desde):
    """Si el cupo se libera de noche, el plazo empieza a correr a las 5:00."""
    return _siguiente_manana(desde) if _de_noche(desde) else desde


def fin_del_plazo(desde, clase):
    """45 minutos "de día" desde `desde` (la noche no cuenta), sin pasar del cierre de la lista."""
    momento = inicio_del_plazo(desde)
    restante = datetime.timedelta(minutes=MINUTOS_PARA_CONFIRMAR)
    while True:
        noche = timezone.make_aware(datetime.datetime.combine(timezone.localtime(momento).date(), NOCHE_DESDE))
        if momento + restante <= noche:
            return min(momento + restante, cierre_de_lista(clase))
        restante -= noche - momento
        momento = _siguiente_manana(noche)


# --- Consultas ---

def mi_puesto(usuario, clase):
    if not usuario.is_authenticated:
        return None
    return clase.lista_espera.filter(usuario=usuario, estado__in=[ListaEspera.ESPERANDO, ListaEspera.OFRECIDO]).first()


def en_espera(clase):
    return clase.lista_espera.filter(estado=ListaEspera.ESPERANDO).count()


def lista_abierta(clase):
    return not clase.cancelada and timezone.now() < cierre_de_lista(clase)


def listas_de(usuario):
    """Sus puestos activos (esperando o con cupo ofrecido), de la clase más próxima a la más lejana."""
    return (usuario.listas_espera.filter(estado__in=[ListaEspera.ESPERANDO, ListaEspera.OFRECIDO])
            .select_related('clase__sala', 'clase__disciplina', 'clase__instructor'))


def ofertas_de(usuario):
    return listas_de(usuario).filter(estado=ListaEspera.OFRECIDO)


def _choca_con_reserva(usuario, clase):
    return Reserva.objects.filter(usuario=usuario, cancelada=False, clase__inicio=clase.inicio).exists()


def motivo_para_no_anotarse(usuario, clase, simular=False):
    """Devuelve el texto de por qué no se puede anotar, o None si se puede."""
    if not lista_abierta(clase):
        return f'La lista de espera se cierra {HORAS_CIERRE} horas antes de la clase.'
    if clase.cupos(simular) > 0:
        return 'Esta clase todavía tiene cupos: puedes reservarla directamente.'
    if clase.reservas.filter(usuario=usuario, cancelada=False).exists():
        return 'Ya tienes una reserva en esta clase.'
    if mi_puesto(usuario, clase):
        return 'Ya estás en la lista de espera de esta clase.'
    if _choca_con_reserva(usuario, clase):
        return 'Ya tienes otra clase reservada a esa misma hora.'
    if listas_de(usuario).count() >= MAXIMO_LISTAS:
        return f'Puedes estar en hasta {MAXIMO_LISTAS} listas de espera a la vez.'
    if compra_para_usar(usuario, clase.fecha) is None:
        return 'SIN_CREDITOS'
    return None


# --- Acciones ---

def anotarse(usuario, clase, simular=False):
    with transaction.atomic():
        clase = Clase.objects.select_for_update().get(pk=clase.pk)
        motivo = motivo_para_no_anotarse(usuario, clase, simular)
        if motivo:
            raise NoSePuedeAnotar(motivo)
        if simular and not clase.ocupacion_fija:
            # Modo demostración: desde ahora las personas de ejemplo cuentan para todos
            clase.ocupacion_fija = True
            clase.save(update_fields=['ocupacion_fija'])
        return ListaEspera.objects.create(usuario=usuario, clase=clase)


def salir(puesto):
    """Sale de la lista (o rechaza el cupo ofrecido, que pasa a la siguiente)."""
    if not puesto.activa:
        return
    ofrecido = puesto.estado == ListaEspera.OFRECIDO
    puesto.estado = ListaEspera.SALIO
    puesto.save(update_fields=['estado'])
    if ofrecido:
        procesar_lista(puesto.clase)


def confirmar(puesto):
    """Confirma el cupo ofrecido: se crea la reserva y se cobra el punto."""
    from notificaciones import avisos

    with transaction.atomic():
        clase = Clase.objects.select_for_update().get(pk=puesto.clase_id)
        puesto = ListaEspera.objects.select_for_update().get(pk=puesto.pk)
        if puesto.estado != ListaEspera.OFRECIDO or timezone.now() >= puesto.oferta_vence:
            raise NoSePuedeAnotar('El plazo para confirmar este cupo ya venció.')
        if _choca_con_reserva(puesto.usuario, clase):
            raise NoSePuedeAnotar('Ya tienes otra clase reservada a esa misma hora.')
        compra = usar_credito(puesto.usuario, clase.fecha)
        if compra is None:
            raise NoSePuedeAnotar('SIN_CREDITOS')
        reserva = Reserva.objects.create(usuario=puesto.usuario, clase=clase, compra=compra)
        puesto.estado, puesto.reserva = ListaEspera.CONFIRMADO, reserva
        puesto.save(update_fields=['estado', 'reserva'])
    avisos.reserva_confirmada(reserva)
    return reserva


def procesar_lista(clase):
    """
    Pone al día la lista de una clase: vence las ofertas cuyo plazo pasó, cierra la lista si
    corresponde y ofrece los cupos libres a las siguientes. Se puede llamar cuantas veces se quiera.
    """
    from notificaciones import avisos

    ahora = timezone.now()
    with transaction.atomic():
        clase = Clase.objects.select_for_update().get(pk=clase.pk)
        for puesto in clase.lista_espera.filter(estado=ListaEspera.OFRECIDO, oferta_vence__lte=ahora):
            puesto.estado = ListaEspera.VENCIDO
            puesto.save(update_fields=['estado'])
            avisos.espera_vencida(puesto)

        esperando = list(clase.lista_espera.filter(estado=ListaEspera.ESPERANDO).select_related('usuario'))
        if not esperando:
            return
        if clase.cancelada or ahora >= cierre_de_lista(clase):
            _cerrar(clase, esperando)
            return

        for puesto in esperando:
            if clase.cupos() <= 0:
                break
            if _choca_con_reserva(puesto.usuario, clase) or compra_para_usar(puesto.usuario, clase.fecha) is None:
                puesto.estado = ListaEspera.OMITIDO
                puesto.save(update_fields=['estado'])
                avisos.espera_omitida(puesto)
                continue
            if inicio_del_plazo(ahora) >= cierre_de_lista(clase):
                # Se liberó de noche y la lista cierra antes de las 5:00: el cupo queda libre para todas
                _cerrar(clase, [p for p in esperando if p.estado == ListaEspera.ESPERANDO])
                return
            puesto.estado = ListaEspera.OFRECIDO
            puesto.oferta_desde, puesto.oferta_vence = ahora, fin_del_plazo(ahora, clase)
            puesto.save(update_fields=['estado', 'oferta_desde', 'oferta_vence'])
            avisos.espera_oferta(puesto)


def _cerrar(clase, esperando):
    from notificaciones import avisos

    hay_cupo = not clase.cancelada and clase.cupos() > 0
    for puesto in esperando:
        puesto.estado = ListaEspera.CERRADO
        puesto.save(update_fields=['estado'])
        avisos.espera_cerrada(puesto, hay_cupo)


def revisar_listas_de_espera():
    """Pone al día todas las listas con puestos activos (ver la nota del inicio)."""
    activas = (Clase.objects.filter(lista_espera__estado__in=[ListaEspera.ESPERANDO, ListaEspera.OFRECIDO])
               .distinct())
    for clase in activas:
        procesar_lista(clase)


def simular_cupo_liberado(clase):
    """SOLO DEMOSTRACIÓN: una persona de ejemplo cancela y el cupo pasa a la lista."""
    if clase.ocupacion_simulada <= 0:
        return False
    Clase.objects.filter(pk=clase.pk).update(ocupacion_simulada=clase.ocupacion_simulada - 1)
    procesar_lista(clase)
    return True
