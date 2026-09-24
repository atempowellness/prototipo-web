"""
Nutrición y masajes: tipos de sesión, horarios de atención de cada profesional y citas.
Las profesionales son las del panel (Clases y horarios → Profesionales, áreas Nutrición y Masajes).

Nota: los nombres en el panel van en masculino ("el turno seleccionado") porque las
frases del panel de Django vienen traducidas así.
"""
import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

from clases.models import DIAS_SEMANA, HORAS_PARA_CANCELAR

NUTRICION, MASAJES = 'nutricion', 'masajes'
SERVICIOS = [(NUTRICION, 'Nutrición'), (MASAJES, 'Masajes')]


class TipoSesion(models.Model):
    servicio = models.CharField(max_length=20, choices=SERVICIOS)
    nombre = models.CharField(max_length=60)
    duracion_minutos = models.PositiveSmallIntegerField('duración (minutos)')
    pide_ficha = models.BooleanField(
        'pide ficha de nutrición', default=False,
        help_text='Si al agendar se pide el formulario breve (objetivo, alergias, condiciones de salud).')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['servicio', 'orden']
        verbose_name, verbose_name_plural = 'tipo de sesión', 'tipos de sesión'

    def __str__(self):
        return f'{self.nombre} ({self.duracion_minutos} min)'


class HorarioAtencion(models.Model):
    """Bloque semanal en que atiende una profesional (por ejemplo, lunes de 9:00 a 13:00)."""
    profesional = models.ForeignKey('clases.Profesional', on_delete=models.CASCADE, related_name='horarios_atencion',
                                    limit_choices_to={'area__in': [NUTRICION, MASAJES]})
    dia_semana = models.PositiveSmallIntegerField('día', choices=DIAS_SEMANA)
    desde = models.TimeField()
    hasta = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['profesional', 'dia_semana', 'desde']
        verbose_name, verbose_name_plural = 'horario de atención', 'horarios de atención'

    def __str__(self):
        return f'{self.profesional} · {self.get_dia_semana_display()} {self.desde:%H:%M}–{self.hasta:%H:%M}'


class Cita(models.Model):
    INCLUIDA, CREDITOS = 'incluida', 'creditos'
    FORMAS = [(INCLUIDA, 'Sesión incluida en el paquete'), (CREDITOS, 'Sesión adicional con puntos')]
    OBJETIVOS = [
        ('energia', 'Tener más energía en el día a día'),
        ('peso', 'Controlar mi peso'),
        ('fuerza', 'Acompañar mi entrenamiento y ganar fuerza'),
        ('digestion', 'Mejorar mi digestión'),
        ('etapa', 'Cuidarme en esta etapa (menopausia, salud ósea…)'),
        ('otro', 'Otro'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='citas')
    profesional = models.ForeignKey('clases.Profesional', on_delete=models.PROTECT, related_name='citas')
    tipo = models.ForeignKey(TipoSesion, on_delete=models.PROTECT, verbose_name='tipo de sesión')
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    forma = models.CharField('cómo se pagó', max_length=10, choices=FORMAS)
    compra = models.ForeignKey('compras.Compra', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='citas', help_text='Si fue incluida: el paquete del que salió la sesión.')
    compras_creditos = models.JSONField('puntos usados (compras)', default=list, blank=True,
                                        help_text='Si fue adicional: de qué compras salieron los puntos.')
    creada = models.DateTimeField(default=timezone.now)
    cancelada = models.BooleanField(default=False)
    cancelada_en = models.DateTimeField(null=True, blank=True)
    devuelta = models.BooleanField('sesión o puntos devueltos', default=False)

    # Ficha breve de nutrición (datos de salud: requieren consentimiento expreso, Ley N.° 29733)
    objetivo = models.CharField(max_length=20, choices=OBJETIVOS, blank=True)
    alergias = models.CharField('alergias o restricciones alimentarias', max_length=200, blank=True)
    condiciones = models.CharField('condiciones de salud', max_length=300, blank=True)
    consentimiento_salud = models.DateTimeField(
        'autorizó el uso de sus datos de salud', null=True, blank=True)

    class Meta:
        ordering = ['inicio']
        # Mismo nombre que las reservas de clases, para que el panel se lea igual en ambas secciones
        verbose_name, verbose_name_plural = 'cupo reservado', 'cupos reservados'

    def __str__(self):
        return f'{self.tipo.nombre} · {self.usuario.nombre_corto} · {timezone.localtime(self.inicio):%d/%m %H:%M}'

    @property
    def servicio(self):
        return self.tipo.servicio

    @property
    def empezo(self):
        return timezone.now() >= self.inicio

    @property
    def se_devuelve_si_cancela(self):
        return self.inicio - timezone.now() >= datetime.timedelta(hours=HORAS_PARA_CANCELAR)
