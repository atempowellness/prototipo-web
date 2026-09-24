"""
Notificaciones de la campanita del encabezado.
Para agregar un tipo nuevo: sumarlo a TIPOS y crear la notificación con `notificar()`.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

MAXIMO_EN_MENU = 10


class Notificacion(models.Model):
    BIENVENIDA = 'bienvenida'
    REFERIDA_REGISTRO = 'referida_registro'
    REFERIDA_COMPRA = 'referida_compra'
    VENCIMIENTO = 'vencimiento'
    CREDITOS_ACTIVADOS = 'creditos_activados'
    CREDITO_EXTRA = 'credito_extra'
    RECORDATORIO = 'recordatorio'
    CLASE_CANCELADA = 'clase_cancelada'
    RESERVA_CONFIRMADA = 'reserva_confirmada'
    AJUSTE_CREDITOS = 'ajuste_creditos'
    CITA_CONFIRMADA = 'cita_confirmada'
    CITA_RECORDATORIO = 'cita_recordatorio'
    CITA_CANCELADA = 'cita_cancelada'
    RECLAMACION = 'reclamacion'
    ENCUENTRO_CONFIRMADO = 'enc_confirmado'
    ENCUENTRO_RECORDATORIO = 'enc_recordatorio'
    ENCUENTRO_CANCELADO = 'enc_cancelado'
    ENCUENTRO_APERTURA = 'enc_apertura'
    TIPOS = [
        (ENCUENTRO_CONFIRMADO, 'Inscripción a un encuentro confirmada'),
        (ENCUENTRO_RECORDATORIO, 'Recordatorio de encuentro'),
        (ENCUENTRO_CANCELADO, 'Encuentro o asistencia cancelada por el estudio'),
        (ENCUENTRO_APERTURA, 'Se abrió la inscripción a un encuentro'),
        (RECLAMACION, 'Libro de reclamaciones'),
        (CITA_CONFIRMADA, 'Cita de nutrición o masajes confirmada'),
        (CITA_RECORDATORIO, 'Recordatorio de cita'),
        (CITA_CANCELADA, 'Cita cancelada por el estudio'),
        (RESERVA_CONFIRMADA, 'Reserva confirmada'),
        (AJUSTE_CREDITOS, 'Ajuste de puntos hecho por el estudio'),
        (RECORDATORIO, 'Recordatorio de clase'),
        (CLASE_CANCELADA, 'Clase cancelada por el estudio'),
        (BIENVENIDA, 'Bienvenida'),
        (REFERIDA_REGISTRO, 'Una amiga se registró con su código'),
        (REFERIDA_COMPRA, 'Una amiga compró con su código'),
        (VENCIMIENTO, 'Puntos por vencer'),
        (CREDITOS_ACTIVADOS, 'Puntos activados (compra)'),
        (CREDITO_EXTRA, 'Punto extra activado (referida)'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    texto = models.CharField(max_length=240)
    enlace = models.CharField(max_length=200, blank=True, help_text='A dónde lleva al tocarla (opcional).')
    creada = models.DateTimeField(default=timezone.now)
    leida = models.BooleanField(default=False)
    compra = models.ForeignKey('compras.Compra', null=True, blank=True, on_delete=models.CASCADE,
                               help_text='En los avisos de vencimiento: la compra que vence (se avisa una sola vez).')
    reserva = models.ForeignKey('clases.Reserva', null=True, blank=True, on_delete=models.CASCADE,
                                help_text='En los recordatorios: la reserva (se recuerda una sola vez).')
    cita = models.ForeignKey('bienestar.Cita', null=True, blank=True, on_delete=models.CASCADE,
                             help_text='En los avisos de nutrición y masajes: la cita.')
    inscripcion = models.ForeignKey('comunidad.Inscripcion', null=True, blank=True, on_delete=models.CASCADE,
                                    help_text='En los avisos de encuentros: la inscripción.')

    class Meta:
        ordering = ['-creada']
        # En masculino por las frases del panel de administración ("el aviso seleccionado")
        verbose_name = 'aviso'
        verbose_name_plural = 'avisos'

    def __str__(self):
        return f'{self.usuario.nombre}: {self.texto}'


def notificar(usuario, tipo, texto, enlace='', compra=None, reserva=None, cita=None, inscripcion=None):
    return Notificacion.objects.create(usuario=usuario, tipo=tipo, texto=texto, enlace=enlace,
                                       compra=compra, reserva=reserva, cita=cita, inscripcion=inscripcion)
