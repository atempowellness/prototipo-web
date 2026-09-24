"""
Encuentros de Atempo Circle (cafés, charlas, salidas y talleres).

- Encuentro: cada actividad, con fecha, lugar y cupo (editable en el panel).
- Inscripcion: una socia apuntada a un encuentro (no gasta puntos).
- AvisoDeApertura: la socia pidió "Recordarme" cuando se abra su inscripción.

Nota: los nombres en el panel van en masculino ("el encuentro seleccionado") porque las
frases del panel de Django vienen traducidas así.
"""
import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

CAFE, CHARLA, SALIDA, TALLER = 'cafe', 'charla', 'salida', 'taller'
TIPOS = [(CAFE, 'Café'), (CHARLA, 'Charla'), (SALIDA, 'Salida'), (TALLER, 'Taller')]
TIPOS_PLURAL = {CAFE: 'Cafés', CHARLA: 'Charlas', SALIDA: 'Salidas', TALLER: 'Talleres'}


class Encuentro(models.Model):
    titulo = models.CharField('título', max_length=80)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    inicio = models.DateTimeField('fecha y hora')
    duracion_minutos = models.PositiveSmallIntegerField('duración (minutos)', default=90)
    lugar = models.CharField(max_length=100)
    descripcion = models.TextField('descripción')
    cupo = models.PositiveSmallIntegerField(default=20, help_text='Dato interno: en la web no se muestra el número.')
    cancelado = models.BooleanField(default=False)
    clave_ejemplo = models.CharField(
        max_length=20, blank=True, editable=False,
        help_text='Solo en los encuentros de ejemplo del prototipo, que se vuelven a crear cuando pasan.')

    class Meta:
        ordering = ['inicio']
        verbose_name, verbose_name_plural = 'encuentro', 'encuentros'

    def __str__(self):
        return f'{self.titulo} · {timezone.localtime(self.inicio):%d/%m %H:%M}'

    @property
    def fecha(self):
        return timezone.localtime(self.inicio).date()

    @property
    def fin(self):
        return self.inicio + datetime.timedelta(minutes=self.duracion_minutos)

    @property
    def empezo(self):
        return timezone.now() >= self.inicio

    @property
    def tipo_plural(self):
        return TIPOS_PLURAL[self.tipo]

    def inscripciones_activas(self):
        return self.inscripciones.filter(cancelada=False)

    def cupos(self):
        return max(self.cupo - self.inscripciones_activas().count(), 0)


class Inscripcion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inscripciones')
    encuentro = models.ForeignKey(Encuentro, on_delete=models.CASCADE, related_name='inscripciones')
    creada = models.DateTimeField(default=timezone.now)
    cancelada = models.BooleanField(default=False)
    cancelada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['encuentro__inicio']
        verbose_name, verbose_name_plural = 'cupo reservado', 'cupos reservados'

    def __str__(self):
        return f'{self.usuario.nombre_corto} → {self.encuentro}'


class AvisoDeApertura(models.Model):
    """La socia pidió que le avisen (en la campanita) cuando se abra su inscripción."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avisos_de_apertura')
    encuentro = models.ForeignKey(Encuentro, on_delete=models.CASCADE, related_name='avisos_de_apertura')
    creado = models.DateTimeField(default=timezone.now)
    avisado = models.BooleanField(default=False)

    class Meta:
        unique_together = [('usuario', 'encuentro')]
        verbose_name, verbose_name_plural = 'pedido de recordatorio', 'pedidos de recordatorio'

    def __str__(self):
        return f'{self.usuario.nombre_corto} → {self.encuentro}'
