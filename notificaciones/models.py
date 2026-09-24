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
    TIPOS = [
        (BIENVENIDA, 'Bienvenida'),
        (REFERIDA_REGISTRO, 'Una amiga se registró con su código'),
        (REFERIDA_COMPRA, 'Una amiga compró con su código'),
        (VENCIMIENTO, 'Créditos por vencer'),
        (CREDITOS_ACTIVADOS, 'Créditos activados (compra)'),
        (CREDITO_EXTRA, 'Crédito extra activado (referida)'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    texto = models.CharField(max_length=240)
    enlace = models.CharField(max_length=200, blank=True, help_text='A dónde lleva al tocarla (opcional).')
    creada = models.DateTimeField(default=timezone.now)
    leida = models.BooleanField(default=False)
    compra = models.ForeignKey('compras.Compra', null=True, blank=True, on_delete=models.CASCADE,
                               help_text='En los avisos de vencimiento: la compra que vence (se avisa una sola vez).')

    class Meta:
        ordering = ['-creada']
        # En masculino por las frases del panel de administración ("el aviso seleccionado")
        verbose_name = 'aviso'
        verbose_name_plural = 'avisos'

    def __str__(self):
        return f'{self.usuario.nombre}: {self.texto}'


def notificar(usuario, tipo, texto, enlace='', compra=None):
    return Notificacion.objects.create(usuario=usuario, tipo=tipo, texto=texto, enlace=enlace, compra=compra)
