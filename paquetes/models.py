from decimal import Decimal

from django.db import models


class Paquete(models.Model):
    """
    Un paquete de créditos (Atempo 1, Atempo 5...). 1 crédito = 1 clase.
    Se editan desde el panel de administración (/admin/).
    """
    nombre = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(
        'dirección web', max_length=40, unique=True,
        help_text='Se usa en la dirección de compra, por ejemplo "atempo-10" → /paquetes/atempo-10/comprar/.',
    )
    creditos = models.PositiveSmallIntegerField('créditos')
    vigencia_meses = models.PositiveSmallIntegerField('vigencia (meses)')
    precio = models.DecimalField('precio (S/)', max_digits=8, decimal_places=2)

    sesiones_nutricion = models.PositiveSmallIntegerField('sesiones de nutrición incluidas', default=0)
    sesiones_masaje = models.PositiveSmallIntegerField('sesiones de masaje incluidas', default=0)
    incluye_circle = models.BooleanField('incluye actividades de Atempo Circle', default=False)
    costo_nutricion_adicional = models.PositiveSmallIntegerField(
        'nutrición adicional (créditos)', null=True, blank=True,
        help_text='Déjalo vacío si este paquete no permite agendar nutrición adicional.',
    )
    costo_masaje_adicional = models.PositiveSmallIntegerField(
        'masaje adicional (créditos)', null=True, blank=True,
        help_text='Déjalo vacío si este paquete no permite agendar masajes adicionales.',
    )

    frase = models.CharField(max_length=120, blank=True, help_text='Aparece en "Ver detalles".')
    etiqueta_destacado = models.CharField(
        'etiqueta destacada', max_length=30, blank=True,
        help_text='Por ejemplo "Más popular". Déjalo vacío si el paquete no se destaca.',
    )
    orden = models.PositiveSmallIntegerField(default=0, help_text='Orden en la página (de menor a mayor).')
    activo = models.BooleanField(default=True, help_text='Desmárcalo para ocultarlo de la web.')

    class Meta:
        ordering = ['orden', 'creditos']

    def __str__(self):
        return self.nombre

    @property
    def precio_por_clase(self):
        return self.precio / self.creditos

    @property
    def ahorro(self):
        """Cuánto se ahorra frente a comprar las mismas clases sueltas."""
        return max(precio_clase_suelta() * self.creditos - self.precio, Decimal(0))

    @property
    def beneficios(self):
        """Lista de lo que incluye, en frases cortas para la tarjeta."""
        lista = []
        if self.creditos == 1:
            lista.append('1 clase presencial de cualquier disciplina')
        else:
            lista.append(f'{self.creditos} clases presenciales')
        if self.sesiones_nutricion:
            s = 'sesión' if self.sesiones_nutricion == 1 else 'sesiones'
            lista.append(f'{self.sesiones_nutricion} {s} con nutricionista')
        if self.sesiones_masaje:
            s = 'sesión' if self.sesiones_masaje == 1 else 'sesiones'
            lista.append(f'{self.sesiones_masaje} {s} de masajes')
        if self.incluye_circle:
            lista.append('Actividades de Atempo Circle')
        return lista


def paquetes_activos():
    return Paquete.objects.filter(activo=True)


def precio_clase_suelta():
    """El precio de la clase suelta es el del paquete de 1 crédito (Atempo 1)."""
    suelta = Paquete.objects.filter(activo=True, creditos=1).first()
    return suelta.precio if suelta else Decimal(65)


def ahorro_maximo_por_clase():
    """La mayor diferencia entre la clase suelta y el precio por clase de un paquete."""
    base = precio_clase_suelta()
    diferencias = [base - p.precio_por_clase for p in paquetes_activos()]
    return max(diferencias, default=Decimal(0))
