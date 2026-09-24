"""
Libro de Reclamaciones virtual (obligatorio para quien vende en el Perú: Código de
Protección y Defensa del Consumidor, Ley N.° 29571, y su reglamento).
Los campos siguen el formato de la Hoja de Reclamación.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

DIAS_HABILES_PARA_RESPONDER = 15   # plazo máximo de respuesta (confirmar con asesoría legal)


class Reclamacion(models.Model):
    RECLAMO, QUEJA = 'reclamo', 'queja'
    TIPOS = [(RECLAMO, 'Reclamo'), (QUEJA, 'Queja')]
    PENDIENTE, RESPONDIDA = 'pendiente', 'respondida'
    ESTADOS = [(PENDIENTE, 'Pendiente de respuesta'), (RESPONDIDA, 'Respondida')]
    SERVICIOS = [
        ('paquete', 'Paquete de puntos'),
        ('clase', 'Clase'),
        ('nutricion', 'Asesoría nutricional'),
        ('masaje', 'Masaje'),
        ('comunidad', 'Actividad de Atempo Circle'),
        ('otro', 'Otro'),
    ]

    numero = models.CharField('n.° de hoja', max_length=12, unique=True, editable=False)
    creada = models.DateTimeField('fecha', default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='reclamaciones', help_text='Si la presentó con la sesión iniciada.')

    # 1. Identificación de quien reclama
    nombre = models.CharField('nombre completo', max_length=120)
    dni = models.CharField('DNI', max_length=12)
    domicilio = models.CharField(max_length=200)
    telefono = models.CharField('teléfono', max_length=15)
    email = models.EmailField('correo electrónico')

    # 2. Identificación del servicio contratado
    servicio = models.CharField('servicio', max_length=20, choices=SERVICIOS)
    monto = models.DecimalField('monto reclamado (S/)', max_digits=8, decimal_places=2, null=True, blank=True)
    descripcion_servicio = models.CharField('descripción del servicio', max_length=200)

    # 3. Detalle
    tipo = models.CharField(max_length=10, choices=TIPOS)
    detalle = models.TextField()
    pedido = models.TextField()

    # 4. Respuesta del estudio
    estado = models.CharField(max_length=12, choices=ESTADOS, default=PENDIENTE)
    respuesta = models.TextField(blank=True, help_text='Acciones adoptadas por el estudio.')
    respondida_en = models.DateTimeField('fecha de respuesta', null=True, blank=True)

    # La clienta puede quitarla de Mi cuenta una vez respondida, pero el estudio la conserva
    # (la norma obliga a guardar las hojas para mostrarlas a INDECOPI si las pide)
    quitada_por_clienta = models.BooleanField('quitada de Mi cuenta por la clienta', default=False)

    class Meta:
        ordering = ['-creada']
        # En masculino por las frases del panel de administración ("el reclamo o queja seleccionado")
        verbose_name, verbose_name_plural = 'reclamo o queja', 'reclamos y quejas'

    def __str__(self):
        return f'Hoja N.° {self.numero} · {self.get_tipo_display()} · {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.numero:
            anio = timezone.localtime(self.creada).year
            ultimo = Reclamacion.objects.filter(numero__startswith=f'{anio}-').order_by('-numero').first()
            siguiente = int(ultimo.numero.split('-')[1]) + 1 if ultimo else 1
            self.numero = f'{anio}-{siguiente:04d}'
        super().save(*args, **kwargs)
