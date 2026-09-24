"""
Cuenta de demostración (SOLO PARA EL PROTOTIPO): una socia de ejemplo con todo en uso,
para recorrer la web completa en la presentación.

Cada vez que se entra, la cuenta vuelve a su estado inicial con fechas actualizadas.
Se arma con las mismas reglas de la web (compra, reservas, cita, encuentro y referidas),
así que todo es coherente: puntos descontados, cupos ocupados, avisos en la campanita.

Nicole tiene:
- Atempo 20 comprado hace 20 días, con 6 clases ya tomadas.
- 2 clases reservadas para los próximos días y 1 cita de nutrición (sesión incluida).
- 1 encuentro de Atempo Circle confirmado y "Recordarme" en otro que aún no abre.
- 2 amigas invitadas: Ana Paula ya compró (Nicole recibió 1 punto de regalo, que vence
  en 5 días, así se ve el aviso de puntos por vencer) y Sofia solo se registró.
"""
import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

CORREO_DEMO = 'demo@atempo.pe'
NOMBRE, APELLIDO = 'Nicole', 'Lucana'
AMIGAS = [
    {'email': 'anapaula.demo@atempo.pe', 'nombre': 'Ana Paula', 'apellido': 'Coloma', 'celular': '900000002',
     'dni': '00000002', 'compra': True},
    {'email': 'sofia.demo@atempo.pe', 'nombre': 'Sofia', 'apellido': 'Montenegro', 'celular': '900000003',
     'dni': '00000003', 'compra': False},
]
CLASES_TOMADAS = 6           # clases "del pasado" (solo se descuentan los puntos)
DIAS_DESDE_LA_COMPRA = 20
DIAS_REGALO_POR_VENCER = 5


def _clase_para(dia, disciplinas):
    """Una clase con cupo de ese día (de preferencia desde las 8:00), de la primera disciplina que tenga."""
    from clases.servicios import clases_del_dia

    for slug in disciplinas:
        clases = [c for c in clases_del_dia(dia, disciplina=slug)
                  if not c.cancelada and c.inicio > timezone.now() and c.cupos() > 0]
        clases.sort(key=lambda c: timezone.localtime(c.inicio).hour < 8)   # primero las de 8:00 en adelante
        if clases:
            return clases[0]
    return None


def _reservar(nicole, dias, disciplinas):
    from clases.servicios import NoSePuedeReservar, reservar
    from notificaciones import avisos

    for n in dias:
        clase = _clase_para(timezone.localdate() + datetime.timedelta(days=n), disciplinas)
        if clase:
            try:
                avisos.reserva_confirmada(reservar(nicole, clase))
                return
            except NoSePuedeReservar:
                continue


def _cita_de_nutricion(nicole):
    from bienestar.models import NUTRICION, TipoSesion
    from bienestar.servicios import NoSePuedeAgendar, agendar, horas_libres
    from notificaciones import avisos

    tipo = TipoSesion.objects.filter(servicio=NUTRICION, pide_ficha=True).first()
    if tipo is None:
        return
    for n in range(3, 8):
        dia = timezone.localdate() + datetime.timedelta(days=n)
        for inicio, profesional in horas_libres(NUTRICION, tipo, dia, usuario=nicole):
            try:
                ficha = {'objetivo': 'etapa', 'consentimiento_salud': timezone.now()}
                avisos.cita_confirmada(agendar(nicole, profesional, tipo, inicio, ficha))
                return
            except NoSePuedeAgendar:
                continue


def _encuentros(nicole):
    from comunidad.models import Encuentro
    from comunidad.servicios import (NoSePuedeInscribir, asegurar_encuentros_de_ejemplo, inscribir,
                                     motivo_para_no_inscribirse, pedir_o_quitar_aviso)
    from notificaciones import avisos

    asegurar_encuentros_de_ejemplo()
    proximos = list(Encuentro.objects.filter(inicio__gt=timezone.now(), cancelado=False))
    # Apuntada al primero que ya esté abierto para ella
    for encuentro in proximos:
        if motivo_para_no_inscribirse(nicole, encuentro) is None:
            try:
                avisos.inscripcion_confirmada(inscribir(nicole, encuentro))
                break
            except NoSePuedeInscribir:
                continue
    # "Recordarme" en el último que todavía no abre para ella
    for encuentro in reversed(proximos):
        if motivo_para_no_inscribirse(nicole, encuentro) == 'AUN_NO':
            pedir_o_quitar_aviso(nicole, encuentro)
            break


@transaction.atomic
def preparar_cuenta_demo():
    """Deja la cuenta de demostración en su estado inicial y la devuelve."""
    from compras.models import registrar_compra, sumar_meses
    from compras.referidas import aplicar_beneficio
    from cuentas.admin import reiniciar_cuenta
    from cuentas.models import generar_codigo_referida
    from notificaciones import avisos
    from paquetes.models import Paquete

    Usuario = get_user_model()
    ahora = timezone.now()

    # 1. La cuenta, limpia (mantiene su código de referida)
    nicole, _ = Usuario.objects.get_or_create(email=CORREO_DEMO, defaults={'celular': '900000001', 'dni': '00000001'})
    reiniciar_cuenta(nicole)
    nicole.nombre, nicole.apellido = NOMBRE, APELLIDO
    prefijo = generar_codigo_referida(NOMBRE).split('-')[0]
    if not nicole.codigo_referida.startswith(prefijo + '-'):   # si cambió el nombre, el código también
        nicole.codigo_referida = generar_codigo_referida(NOMBRE)
    nicole.set_unusable_password()   # solo se entra con el botón de demostración
    nicole.referida_por = None
    nicole.acepto_privacidad = ahora
    nicole.save()
    Usuario.objects.filter(email__endswith='.demo@atempo.pe').delete()   # amigas de ejemplo (también las antiguas)

    # 2. Su Atempo 20, comprado hace 20 días, con 6 clases ya tomadas
    compra = registrar_compra(nicole, Paquete.objects.get(slug='atempo-20'), 'tarjeta', 'Visa •••• 4242')
    compra.fecha = ahora - datetime.timedelta(days=DIAS_DESDE_LA_COMPRA)
    compra.vence = sumar_meses(timezone.localtime(compra.fecha).date(), 3)
    compra.creditos_usados = CLASES_TOMADAS
    compra.save()
    avisos.creditos_activados(compra)

    # 3. Clases, cita y encuentros (con las reglas de siempre)
    from clases.views import asegurar_clases
    asegurar_clases()
    _reservar(nicole, [1, 2, 3], ['pilates', 'yoga'])
    _reservar(nicole, [3, 4, 5], ['pesas', 'zumba'])
    _cita_de_nutricion(nicole)
    _encuentros(nicole)

    # 4. Amigas invitadas: Ana Paula compró (punto de regalo para Nicole) y Sofia solo se registró
    for datos in AMIGAS:
        amiga = Usuario.objects.create_user(datos['email'], None, nombre=datos['nombre'], apellido=datos['apellido'],
                                            celular=datos['celular'], dni=datos['dni'], referida_por=nicole)
        avisos.amiga_se_registro(nicole, amiga)
        if datos['compra']:
            aplicar_beneficio(registrar_compra(amiga, Paquete.objects.get(slug='atempo-5'), 'yape', ''))
    regalo = nicole.compras.filter(tipo='regalo').first()
    if regalo:   # vence pronto, para que se vea el aviso de puntos por vencer
        regalo.vence = timezone.localdate() + datetime.timedelta(days=DIAS_REGALO_POR_VENCER)
        regalo.fecha = timezone.make_aware(datetime.datetime.combine(sumar_meses(regalo.vence, -1),
                                                                     datetime.time(10, 0)))
        regalo.save()

    # 5. Campanita: lo antiguo como leído; quedan sin leer los 3 avisos más recientes
    recientes = list(nicole.notificaciones.values_list('pk', flat=True)[:3])
    nicole.notificaciones.exclude(pk__in=recientes).update(leida=True)
    return nicole
