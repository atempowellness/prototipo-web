from decimal import Decimal

from django.db import models


class Paquete(models.Model):
    """
    Un paquete de puntos (Atempo 1, Atempo 5...). 1 punto = 1 clase.
    Se editan desde el panel de administración (/admin/).
    """
    nombre = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(
        'dirección web', max_length=40, unique=True,
        help_text='Se usa en la dirección de compra, por ejemplo "atempo-10" → /paquetes/atempo-10/comprar/.',
    )
    creditos = models.PositiveSmallIntegerField('puntos')
    vigencia_meses = models.PositiveSmallIntegerField('vigencia (meses)')
    precio = models.DecimalField('precio (S/)', max_digits=8, decimal_places=2)

    sesiones_nutricion = models.PositiveSmallIntegerField('sesiones de nutrición incluidas', default=0)
    sesiones_masaje = models.PositiveSmallIntegerField('sesiones de masaje incluidas', default=0)
    incluye_circle = models.BooleanField('incluye actividades de Atempo Circle', default=False)
    dias_inscripcion_circle = models.PositiveSmallIntegerField(
        'inscripción a encuentros (días antes)', null=True, blank=True,
        help_text='Con cuántos días de anticipación se abre la inscripción a los encuentros de Atempo Circle '
                  'para quien tiene este paquete. Más días = se inscribe antes. Solo cuenta si incluye Atempo Circle.',
    )
    costo_nutricion_adicional = models.PositiveSmallIntegerField(
        'nutrición adicional (puntos)', null=True, blank=True,
        help_text='Déjalo vacío si este paquete no permite agendar nutrición adicional.',
    )
    costo_masaje_adicional = models.PositiveSmallIntegerField(
        'masaje adicional (puntos)', null=True, blank=True,
        help_text='Déjalo vacío si este paquete no permite agendar masajes adicionales.',
    )

    frase = models.CharField(max_length=120, blank=True, help_text='Aparece en "Ver detalles".')
    etiqueta_destacado = models.CharField(
        'etiqueta destacada', max_length=30, blank=True,
        help_text='Por ejemplo "Más popular". Déjalo vacío si el paquete no se destaca.',
    )
    orden = models.PositiveSmallIntegerField(default=0, help_text='Orden en la página (de menor a mayor).')
    activo = models.BooleanField(default=True, help_text='Desmárcalo para ocultarlo de la web.')

    # Preventa Founding Members: un paquete aparte, solo para la primera compra y con ventas limitadas
    es_founding = models.BooleanField(
        'paquete Founding Members', default=False,
        help_text='Se muestra aparte, solo lo pueden comprar cuentas sin compras anteriores y desaparece al '
                  'llegar al máximo de ventas. Quien lo compra lleva la insignia de Founding Member.')
    ventas_maximas = models.PositiveSmallIntegerField(
        'ventas máximas', null=True, blank=True, help_text='Solo para Founding Members (por ejemplo 100).')
    precio_referencia = models.DecimalField(
        'precio de referencia (S/)', max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Solo para Founding Members: el precio normal, que se muestra tachado junto al precio especial.')

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

    # --- Founding Members ---
    @property
    def vendidos(self):
        return self.compras.filter(tipo='compra').count()

    @property
    def quedan(self):
        return max((self.ventas_maximas or 0) - self.vendidos, 0)


def paquetes_activos():
    """Los paquetes de siempre (sin Founding Members, que se muestra aparte y no cuenta para precios ni ahorros)."""
    return Paquete.objects.filter(activo=True, es_founding=False)


def paquete_founding():
    """El paquete Founding Members si está activo y le quedan ventas; si no, None."""
    paquete = Paquete.objects.filter(activo=True, es_founding=True).first()
    return paquete if paquete and paquete.quedan > 0 else None


def puede_comprar_founding(usuario):
    """Solo como primera compra: cuentas sin compras pagadas anteriores."""
    return not usuario.is_authenticated or not usuario.compras.filter(tipo='compra').exists()


def precio_clase_suelta():
    """El precio de la clase suelta es el del paquete de 1 punto (Atempo 1)."""
    suelta = Paquete.objects.filter(activo=True, es_founding=False, creditos=1).first()
    return suelta.precio if suelta else Decimal(65)


def ahorro_maximo_por_clase():
    """La mayor diferencia entre la clase suelta y el precio por clase de un paquete."""
    base = precio_clase_suelta()
    diferencias = [base - p.precio_por_clase for p in paquetes_activos()]
    return max(diferencias, default=Decimal(0))
