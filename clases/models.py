"""
Clases, horarios y reservas.

- Sala, Disciplina y Profesional: los datos fijos del estudio (editables en el panel).
- HorarioBase: la semana tipo ("lunes 7:30, Sala Calma: Pilates Suave con …").
- Clase: cada clase concreta de un día (se crean solas a partir del horario base).
- Reserva: una clienta en una clase, con el punto que usó.

Nota: los nombres en el panel van en masculino ("el salón seleccionado") porque las
frases del panel de Django vienen traducidas así.
"""
import datetime
import random

from django.conf import settings
from django.db import models
from django.utils import timezone

AFORO = 12                    # dato interno: en la web se habla de "grupos reducidos"
DURACION_MINUTOS = 50
DIAS_PARA_RESERVAR = 7        # hasta cuántos días hacia adelante se puede reservar
HORAS_PARA_CANCELAR = 12      # con esta anticipación o más, el punto se devuelve
OCUPACION_SIMULADA = (3, 10)  # personas "de ejemplo" por clase en el modo simulación

NIVELES = [('suave', 'Suave'), ('media', 'Media'), ('activa', 'Activa')]
DIAS_SEMANA = [(0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'),
               (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo')]


class Sala(models.Model):
    nombre = models.CharField(max_length=40, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name, verbose_name_plural = 'salón', 'salones'

    def __str__(self):
        return self.nombre


class Disciplina(models.Model):
    nombre = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True)
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT, related_name='disciplinas')
    frase = models.CharField(max_length=160)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name, verbose_name_plural = 'tipo de clase', 'tipos de clase'

    def __str__(self):
        return self.nombre


class Profesional(models.Model):
    """Equipo del estudio: instructores, nutricionistas y masajistas (se muestran en Nosotros)."""
    INSTRUCCION, NUTRICION, MASAJES = 'instruccion', 'nutricion', 'masajes'
    AREAS = [(INSTRUCCION, 'Instrucción de clases'), (NUTRICION, 'Nutrición'), (MASAJES, 'Masajes')]

    nombre = models.CharField(max_length=60)
    area = models.CharField(max_length=20, choices=AREAS, default=INSTRUCCION)
    rol = models.CharField(max_length=60, help_text='Lo que se muestra bajo el nombre, por ejemplo "Pilates y Yoga".')
    disciplinas = models.ManyToManyField(Disciplina, blank=True, related_name='profesionales')
    frase = models.CharField(max_length=160, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name, verbose_name_plural = 'profesional', 'profesionales'

    def __str__(self):
        return self.nombre

    @property
    def iniciales(self):
        palabras = [p for p in self.nombre.split() if not p.endswith('.')]
        return (palabras[0][0] + (palabras[-1][0] if len(palabras) > 1 else '')).upper()


class HorarioBase(models.Model):
    """La semana tipo. A partir de aquí se crean las clases de cada día."""
    dia_semana = models.PositiveSmallIntegerField('día', choices=DIAS_SEMANA)
    hora = models.TimeField()
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    instructor = models.ForeignKey(Profesional, on_delete=models.PROTECT,
                                   limit_choices_to={'area': Profesional.INSTRUCCION})
    nivel = models.CharField(max_length=10, choices=NIVELES)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['dia_semana', 'hora', 'sala__orden']
        unique_together = [('dia_semana', 'hora', 'sala')]
        verbose_name, verbose_name_plural = 'horario base', 'horarios base'

    def __str__(self):
        return f'{self.get_dia_semana_display()} {self.hora:%H:%M} · {self.sala} · {self.disciplina}'


class Clase(models.Model):
    """Una clase concreta (por ejemplo, el lunes 29 a las 7:30 en Sala Calma)."""
    inicio = models.DateTimeField()
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    instructor = models.ForeignKey(Profesional, on_delete=models.PROTECT)
    nivel = models.CharField(max_length=10, choices=NIVELES)
    aforo = models.PositiveSmallIntegerField(default=AFORO)
    ocupacion_simulada = models.PositiveSmallIntegerField(
        default=0, help_text='Personas "de ejemplo", solo se cuentan en el modo simulación.')
    ocupacion_fija = models.BooleanField(
        'personas de ejemplo siempre', default=False,
        help_text='Se activa cuando alguien usa la lista de espera en el modo demostración: desde ahí, las '
                  'personas de ejemplo cuentan para todos (así la clase sigue llena y la lista tiene sentido).')
    cancelada = models.BooleanField(default=False)
    motivo_cancelacion = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['inicio', 'sala__orden']
        unique_together = [('inicio', 'sala')]
        verbose_name, verbose_name_plural = 'horario programado', 'horarios programados'

    def __str__(self):
        local = timezone.localtime(self.inicio)
        return f'{self.disciplina} · {local:%d/%m %H:%M} · {self.sala}'

    @property
    def fin(self):
        return self.inicio + datetime.timedelta(minutes=DURACION_MINUTOS)

    @property
    def fecha(self):
        return timezone.localtime(self.inicio).date()

    @property
    def empezo(self):
        return timezone.now() >= self.inicio

    def reservas_activas(self):
        return self.reservas.filter(cancelada=False)

    def ofertas_activas(self):
        """Cupos guardados para alguien de la lista de espera mientras decide."""
        return self.lista_espera.filter(estado=ListaEspera.OFRECIDO)

    def ocupados(self, simular=False):
        ejemplo = self.ocupacion_simulada if (simular or self.ocupacion_fija) else 0
        return self.reservas_activas().count() + self.ofertas_activas().count() + ejemplo

    def cupos(self, simular=False):
        return max(self.aforo - self.ocupados(simular), 0)


class Reserva(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservas')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='reservas')
    compra = models.ForeignKey('compras.Compra', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='reservas', help_text='De qué compra salió el punto.')
    creada = models.DateTimeField(default=timezone.now)
    cancelada = models.BooleanField(default=False)
    cancelada_en = models.DateTimeField(null=True, blank=True)
    credito_devuelto = models.BooleanField(default=False)

    class Meta:
        ordering = ['clase__inicio']
        verbose_name, verbose_name_plural = 'cupo reservado', 'cupos reservados'

    def __str__(self):
        return f'{self.usuario.nombre_corto} → {self.clase}'

    @property
    def se_devuelve_si_cancela(self):
        """¿Faltan 12 horas o más?"""
        return self.clase.inicio - timezone.now() >= datetime.timedelta(hours=HORAS_PARA_CANCELAR)


class ListaEspera(models.Model):
    """
    Un puesto en la lista de espera de una clase llena. Cuando se libera un cupo, se le
    ofrece a la primera que espera, con un plazo para confirmar (ver clases/lista_espera.py).
    """
    ESPERANDO, OFRECIDO, CONFIRMADO = 'esperando', 'ofrecido', 'confirmado'
    VENCIDO, OMITIDO, SALIO, CERRADO = 'vencido', 'omitido', 'salio', 'cerrado'
    ESTADOS = [
        (ESPERANDO, 'Esperando'),
        (OFRECIDO, 'Cupo ofrecido: esperando que confirme'),
        (CONFIRMADO, 'Confirmó: tiene reserva'),
        (VENCIDO, 'No confirmó a tiempo'),
        (OMITIDO, 'Se saltó (sin punto vigente u otra clase a esa hora)'),
        (SALIO, 'Salió de la lista'),
        (CERRADO, 'La lista se cerró'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listas_espera')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='lista_espera')
    creada = models.DateTimeField('se anotó', default=timezone.now)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ESPERANDO)
    oferta_desde = models.DateTimeField('cupo ofrecido el', null=True, blank=True)
    oferta_vence = models.DateTimeField('plazo para confirmar', null=True, blank=True)
    reserva = models.ForeignKey(Reserva, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['clase__inicio', 'creada']
        verbose_name, verbose_name_plural = 'puesto en lista de espera', 'puestos en lista de espera'

    def __str__(self):
        return f'{self.usuario.nombre_corto} → {self.clase}'

    @property
    def activa(self):
        return self.estado in (self.ESPERANDO, self.OFRECIDO)

    @property
    def puesto(self):
        """1 = la siguiente en recibir un cupo."""
        if self.estado != self.ESPERANDO:
            return None
        return self.clase.lista_espera.filter(estado=self.ESPERANDO, creada__lt=self.creada).count() + 1


def numero_simulado():
    return random.randint(*OCUPACION_SIMULADA)
