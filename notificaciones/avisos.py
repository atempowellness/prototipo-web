"""
Textos de cada notificación, en un solo lugar para editarlos fácilmente.
"""
import datetime

from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from .models import Notificacion, notificar


def _fecha(dia):
    return date_format(dia, 'j \\d\\e F')


def creditos_activados(compra):
    """Después de pagar un paquete."""
    if compra.creditos == 1:
        texto = f'Se activó tu punto de {compra.nombre_paquete}. Puedes usarlo hasta el {_fecha(compra.vence)}.'
    else:
        texto = (f'Se activaron tus {compra.creditos} puntos de {compra.nombre_paquete}. '
                 f'Puedes usarlos hasta el {_fecha(compra.vence)}.')
    notificar(compra.usuario, Notificacion.CREDITOS_ACTIVADOS, texto, reverse('cuenta'))


def credito_extra_activado(regalo, invitadora):
    """A la amiga nueva, cuando se activa su punto extra por referida."""
    notificar(regalo.usuario, Notificacion.CREDITO_EXTRA,
              f'Se activó tu punto extra por venir invitada por {invitadora.nombre}. '
              f'Puedes usarlo hasta el {_fecha(regalo.vence)}.',
              reverse('cuenta'))


def bienvenida(usuario):
    notificar(usuario, Notificacion.BIENVENIDA,
              f'¡Bienvenida a Atempo, {usuario.nombre}! Elige tu paquete y reserva tu primera clase.',
              reverse('paquetes'))


def amiga_se_registro(invitadora, amiga):
    notificar(invitadora, Notificacion.REFERIDA_REGISTRO,
              f'{amiga.nombre_corto} se registró con tu código. Cuando compre su primer paquete desde '
              f'Atempo 5, las dos reciben 1 punto.',
              reverse('cuenta'))


def amiga_compro(invitadora, amiga, regalo):
    """A quien invitó. `regalo` es su punto de regalo, o None si ya llegó al tope del mes."""
    if regalo is not None:
        texto = (f'¡{amiga.nombre_corto} compró su paquete con tu código! Se activó tu punto de regalo: '
                 f'puedes usarlo hasta el {_fecha(regalo.vence)}.')
    else:
        texto = (f'{amiga.nombre_corto} compró su paquete con tu código. Este mes ya llegaste al tope '
                 f'de 5 puntos por referidas.')
    notificar(invitadora, Notificacion.REFERIDA_COMPRA, texto, reverse('cuenta'))


def _clase_texto(clase):
    local = timezone.localtime(clase.inicio)
    return f'{clase.disciplina.nombre} a las {local:%H:%M} en {clase.sala.nombre}'


def revisar_recordatorios(usuario):
    """
    Recuerda cada clase reservada cuando faltan 24 horas o menos (una sola vez por reserva).
    Se revisa al cargar cualquier página; en la versión real sería una tarea automática.
    """
    ahora = timezone.now()
    ya_avisadas = set(usuario.notificaciones.filter(tipo=Notificacion.RECORDATORIO)
                      .values_list('reserva_id', flat=True))
    reservas = (usuario.reservas.filter(cancelada=False, clase__inicio__gt=ahora,
                                        clase__inicio__lte=ahora + datetime.timedelta(hours=24))
                .select_related('clase__disciplina', 'clase__sala'))
    for reserva in reservas:
        if reserva.pk in ya_avisadas:
            continue
        dia = 'Hoy' if reserva.clase.fecha == timezone.localdate() else 'Mañana'
        notificar(usuario, Notificacion.RECORDATORIO,
                  f'{dia} tienes {_clase_texto(reserva.clase)}. ¡Te esperamos!',
                  reverse('cuenta'), reserva=reserva)


def reserva_confirmada(reserva):
    clase = reserva.clase
    dia = date_format(timezone.localtime(clase.inicio), 'l j \\d\\e F')
    notificar(reserva.usuario, Notificacion.RESERVA_CONFIRMADA,
              f'Reserva confirmada: {_clase_texto(clase)}, el {dia}. '
              f'Te enviamos un correo de confirmación: presenta tu DNI en recepción.',
              reverse('cuenta'), reserva=reserva)


def inasistencias(usuaria):
    """Aviso amable (una vez por mes) tras varias clases reservadas a las que no pudo venir."""
    from clases.asistencia import INASISTENCIAS_PARA_AVISO
    notificar(usuaria, Notificacion.INASISTENCIAS,
              f'Notamos que este mes no pudiste venir a {INASISTENCIAS_PARA_AVISO} clases que reservaste. '
              f'Si no puedes asistir, cancela antes: liberas tu cupo para otra socia y, con 12 horas o más, '
              f'recuperas tu punto.', reverse('cuenta'))


def _clase_con_dia(clase):
    local = timezone.localtime(clase.inicio)
    return f'{_clase_texto(clase)} del {date_format(local, "l j \\d\\e F")}'


def _hasta(momento):
    """'las 10:45' si es hoy; 'mañana a las 5:45' o 'el martes 3 a las 5:45' si no."""
    local = timezone.localtime(momento)
    hoy = timezone.localdate()
    if local.date() == hoy:
        return f'las {local:%H:%M}'
    if local.date() == hoy + datetime.timedelta(days=1):
        return f'mañana a las {local:%H:%M}'
    return f'el {date_format(local, "l j")} a las {local:%H:%M}'


def _enlace_clase(clase):
    return reverse('horarios') + f'?dia={clase.fecha.isoformat()}'


def espera_oferta(puesto):
    notificar(puesto.usuario, Notificacion.ESPERA_OFERTA,
              f'¡Se liberó un cupo para ti en {_clase_con_dia(puesto.clase)}! Confírmalo hasta '
              f'{_hasta(puesto.oferta_vence)}. También te enviamos un correo.', _enlace_clase(puesto.clase))


def espera_vencida(puesto):
    notificar(puesto.usuario, Notificacion.ESPERA_VENCIDA,
              f'Venció el plazo para confirmar el cupo de {_clase_con_dia(puesto.clase)}. '
              f'Se lo ofrecimos a la siguiente persona de la lista.', _enlace_clase(puesto.clase))


def espera_omitida(puesto):
    notificar(puesto.usuario, Notificacion.ESPERA_FIN,
              f'Se liberó un cupo en {_clase_con_dia(puesto.clase)}, pero no tenías un punto vigente para ese día '
              f'u otra clase a esa hora, así que pasó a la siguiente persona.', _enlace_clase(puesto.clase))


def espera_cerrada(puesto, hay_cupo):
    clase = puesto.clase
    if clase.cancelada:
        texto = f'El estudio canceló la clase de {_clase_con_dia(clase)}, así que saliste de su lista de espera.'
    elif hay_cupo:
        texto = (f'Se liberó un cupo en {_clase_con_dia(clase)}. Como la lista de espera ya cerró, '
                 f'puedes reservarlo directamente si aún quieres ir.')
    else:
        texto = (f'La lista de espera de {_clase_con_dia(clase)} cerró y no se liberó ningún cupo. '
                 f'¡Te esperamos en otra clase!')
    notificar(puesto.usuario, Notificacion.ESPERA_FIN, texto, _enlace_clase(clase))


def ajuste_de_creditos(usuario, cantidad, motivo=''):
    """El estudio sumó (cantidad > 0) o quitó (cantidad < 0) puntos desde el panel."""
    n = abs(cantidad)
    creditos = 'punto' if n == 1 else 'puntos'
    if cantidad > 0:
        texto = f'El estudio agregó {n} {creditos} a tu cuenta.'
    else:
        texto = f'El estudio descontó {n} {creditos} de tu cuenta.'
    if motivo:
        texto += f' Motivo: {motivo}.'
    notificar(usuario, Notificacion.AJUSTE_CREDITOS, texto, reverse('cuenta'))


def _cita_texto(cita):
    local = timezone.localtime(cita.inicio)
    return f'{cita.tipo.nombre} con {cita.profesional.nombre}, el {date_format(local, "l j \\d\\e F")} a las {local:%H:%M}'


def cita_confirmada(cita):
    como = ('Se usó 1 sesión incluida en tu paquete.' if cita.forma == 'incluida'
            else f'Se usaron {len(cita.compras_creditos)} puntos.' if len(cita.compras_creditos) != 1
            else 'Se usó 1 punto.')
    notificar(cita.usuario, Notificacion.CITA_CONFIRMADA,
              f'Cita confirmada: {_cita_texto(cita)}. {como}', reverse('cuenta'), cita=cita)


def cita_cancelada(cita, devuelta):
    texto = f'El estudio canceló tu cita: {_cita_texto(cita)}.'
    if devuelta:
        texto += ' Te devolvimos la sesión.' if cita.forma == 'incluida' else ' Te devolvimos los puntos.'
    notificar(cita.usuario, Notificacion.CITA_CANCELADA, texto, reverse('bienestar'), cita=cita)


def revisar_recordatorios_de_citas(usuario):
    """Recuerda cada cita cuando faltan 24 horas o menos (una sola vez por cita)."""
    ahora = timezone.now()
    ya_avisadas = set(usuario.notificaciones.filter(tipo=Notificacion.CITA_RECORDATORIO)
                      .values_list('cita_id', flat=True))
    citas = (usuario.citas.filter(cancelada=False, inicio__gt=ahora, inicio__lte=ahora + datetime.timedelta(hours=24))
             .select_related('tipo', 'profesional'))
    for cita in citas:
        if cita.pk in ya_avisadas:
            continue
        dia = 'Hoy' if timezone.localtime(cita.inicio).date() == timezone.localdate() else 'Mañana'
        local = timezone.localtime(cita.inicio)
        notificar(usuario, Notificacion.CITA_RECORDATORIO,
                  f'{dia} tienes tu cita de {cita.tipo.nombre.lower()} con {cita.profesional.nombre} '
                  f'a las {local:%H:%M}. ¡Te esperamos!', reverse('cuenta'), cita=cita)


def reserva_cancelada_por_estudio(reserva, devuelto):
    """El estudio canceló la reserva de una clienta (la clase sigue en pie)."""
    clase = reserva.clase
    dia = date_format(timezone.localtime(clase.inicio), 'l j \\d\\e F')
    texto = f'El estudio canceló tu reserva de {_clase_texto(clase)} del {dia}.'
    texto += ' Te devolvimos tu punto.' if devuelto else ''
    notificar(reserva.usuario, Notificacion.CLASE_CANCELADA, texto, reverse('horarios'), reserva=reserva)


def reclamacion_recibida(reclamacion):
    from legal.models import DIAS_HABILES_PARA_RESPONDER
    notificar(reclamacion.usuario, Notificacion.RECLAMACION,
              f'Recibimos tu {reclamacion.get_tipo_display().lower()} (hoja N.° {reclamacion.numero}). '
              f'Te responderemos en un plazo máximo de {DIAS_HABILES_PARA_RESPONDER} días hábiles.',
              reverse('cuenta') + '#reclamos')


def reclamacion_respondida(reclamacion):
    notificar(reclamacion.usuario, Notificacion.RECLAMACION,
              f'Respondimos tu {reclamacion.get_tipo_display().lower()} (hoja N.° {reclamacion.numero}). '
              f'Puedes verla en Mi cuenta. También te la enviamos a {reclamacion.email}.',
              reverse('cuenta') + '#reclamos')


def _encuentro_texto(encuentro):
    local = timezone.localtime(encuentro.inicio)
    return f'{encuentro.titulo}, el {date_format(local, "l j \\d\\e F")} a las {local:%H:%M}'


def inscripcion_confirmada(inscripcion):
    notificar(inscripcion.usuario, Notificacion.ENCUENTRO_CONFIRMADO,
              f'Te apuntaste a {_encuentro_texto(inscripcion.encuentro)}. Si no puedes ir, cancela '
              f'para liberar tu cupo.', reverse('cuenta') + '#encuentros', inscripcion=inscripcion)


def inscripcion_cancelada_por_estudio(inscripcion):
    notificar(inscripcion.usuario, Notificacion.ENCUENTRO_CANCELADO,
              f'El estudio canceló tu asistencia a {_encuentro_texto(inscripcion.encuentro)}.',
              reverse('comunidad'), inscripcion=inscripcion)


def encuentro_cancelado(inscripcion):
    notificar(inscripcion.usuario, Notificacion.ENCUENTRO_CANCELADO,
              f'El estudio canceló el encuentro {_encuentro_texto(inscripcion.encuentro)}. '
              f'Lo sentimos: te esperamos en el próximo.', reverse('comunidad'), inscripcion=inscripcion)


def revisar_recordatorios_de_encuentros(usuario):
    """Recuerda cada encuentro cuando faltan 24 horas o menos (una sola vez por inscripción)."""
    ahora = timezone.now()
    ya_avisadas = set(usuario.notificaciones.filter(tipo=Notificacion.ENCUENTRO_RECORDATORIO)
                      .values_list('inscripcion_id', flat=True))
    inscripciones = (usuario.inscripciones.filter(cancelada=False, encuentro__inicio__gt=ahora,
                                                  encuentro__inicio__lte=ahora + datetime.timedelta(hours=24))
                     .select_related('encuentro'))
    for inscripcion in inscripciones:
        if inscripcion.pk in ya_avisadas:
            continue
        encuentro = inscripcion.encuentro
        local = timezone.localtime(encuentro.inicio)
        dia = 'Hoy' if local.date() == timezone.localdate() else 'Mañana'
        notificar(usuario, Notificacion.ENCUENTRO_RECORDATORIO,
                  f'{dia} es {encuentro.titulo}, a las {local:%H:%M} en {encuentro.lugar}. ¡Te esperamos!',
                  reverse('cuenta') + '#encuentros', inscripcion=inscripcion)


def revisar_aperturas(usuario):
    """Avisa (una sola vez) cuando se abre la inscripción a un encuentro que pidió "Recordarme"."""
    from comunidad.servicios import apertura_para

    hoy = timezone.localdate()
    pedidos = usuario.avisos_de_apertura.filter(avisado=False, encuentro__cancelado=False,
                                                encuentro__inicio__gt=timezone.now()).select_related('encuentro')
    for pedido in pedidos:
        apertura = apertura_para(usuario, pedido.encuentro)
        if apertura is None or apertura > hoy:
            continue
        notificar(usuario, Notificacion.ENCUENTRO_APERTURA,
                  f'Ya puedes apuntarte a {_encuentro_texto(pedido.encuentro)}. También te enviamos un correo.',
                  reverse('comunidad'))
        pedido.avisado = True
        pedido.save(update_fields=['avisado'])


def clase_cancelada(reserva, credito_devuelto):
    clase = reserva.clase
    dia = date_format(timezone.localtime(clase.inicio), 'l j \\d\\e F')
    texto = f'El estudio canceló la clase de {_clase_texto(clase)} del {dia}.'
    texto += ' Te devolvimos tu punto.' if credito_devuelto else ''
    notificar(reserva.usuario, Notificacion.CLASE_CANCELADA, texto, reverse('horarios'), reserva=reserva)


def revisar_vencimientos(usuario):
    """
    Crea el aviso de puntos por vencer (7 días o menos) una sola vez por compra.
    Se revisa al cargar cualquier página; en la versión real sería una tarea diaria.
    """
    from compras.models import compras_vigentes

    ya_avisadas = set(usuario.notificaciones.filter(tipo=Notificacion.VENCIMIENTO)
                      .values_list('compra_id', flat=True))
    for compra in compras_vigentes(usuario):
        if compra.vence_pronto and compra.pk not in ya_avisadas:
            origen = compra.origen
            fecha = _fecha(compra.vence)
            if compra.creditos_disponibles == 1:
                texto = f'Te queda 1 punto {origen} y vence el {fecha}. ¡Reserva tu clase!'
            else:
                texto = (f'Te quedan {compra.creditos_disponibles} puntos {origen} y vencen el {fecha}. '
                         f'¡Reserva tus clases!')
            notificar(usuario, Notificacion.VENCIMIENTO, texto, reverse('horarios'), compra=compra)
