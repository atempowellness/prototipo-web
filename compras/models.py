"""
Compras de paquetes. Cada compra es una "bolsa" de créditos con su propia vigencia,
que empieza el día de la compra. Se guarda una copia de los datos del paquete
(nombre, créditos, precio...) para que el historial no cambie si luego se edita
el paquete en el panel.
"""
import calendar
import datetime
import random
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone

IGV = Decimal('0.18')
DIAS_AVISO_VENCIMIENTO = 7


def sumar_meses(fecha, meses):
    """23/10 + 1 mes = 23/11; 31/01 + 1 mes = 28/02 (o 29 en año bisiesto)."""
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return datetime.date(anio, mes, dia)


class Compra(models.Model):
    """
    Una "bolsa" de créditos con su vigencia. Normalmente es una compra pagada; también
    puede ser un crédito de regalo del programa de referidas (tipo REGALO, precio S/ 0,
    sin paquete ni boleta), que sigue las mismas reglas de vigencia y uso.
    """
    TARJETA, YAPE, PLIN = 'tarjeta', 'yape', 'plin'
    METODOS = [(TARJETA, 'Tarjeta'), (YAPE, 'Yape'), (PLIN, 'Plin')]
    COMPRA, REGALO = 'compra', 'regalo'
    TIPOS = [(COMPRA, 'Compra'), (REGALO, 'Crédito de regalo por referida')]

    tipo = models.CharField(max_length=10, choices=TIPOS, default=COMPRA)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='compras')
    paquete = models.ForeignKey('paquetes.Paquete', on_delete=models.PROTECT, related_name='compras',
                                null=True, blank=True)
    referida = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='por la referida de', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='regalos_generados',
        help_text='En los créditos de regalo: la amiga cuya primera compra generó este crédito.')
    fecha = models.DateTimeField('fecha de compra', default=timezone.now)
    vence = models.DateField('vence el', help_text='Los créditos se pueden usar hasta este día, inclusive.')

    # Copia de los datos del paquete al momento de la compra
    nombre_paquete = models.CharField('paquete comprado', max_length=40)
    creditos = models.PositiveSmallIntegerField('créditos')
    precio_pagado = models.DecimalField('precio pagado (S/)', max_digits=8, decimal_places=2)
    sesiones_nutricion = models.PositiveSmallIntegerField('nutrición incluida', default=0)
    sesiones_masaje = models.PositiveSmallIntegerField('masajes incluidos', default=0)
    incluye_circle = models.BooleanField('incluye Atempo Circle', default=False)

    # Uso
    creditos_usados = models.PositiveSmallIntegerField('créditos usados', default=0)
    nutricion_usada = models.PositiveSmallIntegerField('nutrición usada', default=0)
    masaje_usado = models.PositiveSmallIntegerField('masajes usados', default=0)

    # Pago (simulado). De la tarjeta solo se guardan los últimos 4 dígitos.
    metodo = models.CharField('medio de pago', max_length=10, choices=METODOS, blank=True)
    detalle_pago = models.CharField('detalle del pago', max_length=60, blank=True)
    numero_operacion = models.CharField('n.° de operación', max_length=12, blank=True)

    class Meta:
        ordering = ['-fecha']
        # En masculino: las frases del panel vienen traducidas así ("el pago seleccionado")
        verbose_name = 'pago'
        verbose_name_plural = 'pagos'

    def __str__(self):
        return f'{self.nombre_paquete} – {self.usuario.get_full_name()} ({self.fecha:%d/%m/%Y})'

    @property
    def es_regalo(self):
        return self.tipo == self.REGALO

    # --- Créditos y beneficios ---
    @property
    def creditos_disponibles(self):
        return self.creditos - self.creditos_usados

    @property
    def nutricion_disponible(self):
        return self.sesiones_nutricion - self.nutricion_usada

    @property
    def masaje_disponible(self):
        return self.sesiones_masaje - self.masaje_usado

    @property
    def vigente(self):
        return timezone.localdate() <= self.vence

    @property
    def dias_para_vencer(self):
        return (self.vence - timezone.localdate()).days

    @property
    def vence_pronto(self):
        """Le quedan créditos y vence en 7 días o menos."""
        return self.vigente and self.creditos_disponibles > 0 and self.dias_para_vencer <= DIAS_AVISO_VENCIMIENTO

    # --- Boleta (simulada) ---
    @property
    def numero_boleta(self):
        return f'B001-{self.pk:08d}'

    @property
    def subtotal(self):
        return (self.precio_pagado / (1 + IGV)).quantize(Decimal('0.01'))

    @property
    def igv(self):
        return self.precio_pagado - self.subtotal


# --- Consultas por clienta ---

def compras_vigentes(usuario):
    """Compras que aún no vencen, de la que vence antes a la que vence después."""
    return usuario.compras.filter(vence__gte=timezone.localdate()).order_by('vence', 'fecha')


def creditos_disponibles(usuario):
    total = compras_vigentes(usuario).aggregate(
        total=Sum(F('creditos') - F('creditos_usados')))['total']
    return total or 0


def tiene_atempo_circle(usuario):
    return compras_vigentes(usuario).filter(incluye_circle=True).exists()


def usar_credito(usuario):
    """
    Descuenta 1 crédito de la compra vigente que vence antes (para no perder créditos).
    Los créditos vencidos no se pueden usar. Devuelve la compra usada o None si no tiene.
    La usarán las reservas de clases.
    """
    with transaction.atomic():
        compra = (compras_vigentes(usuario).select_for_update()
                  .filter(creditos_usados__lt=F('creditos')).first())
        if compra is None:
            return None
        compra.creditos_usados = F('creditos_usados') + 1
        compra.save(update_fields=['creditos_usados'])
        compra.refresh_from_db()
        return compra


def compras_pagadas(usuario):
    """Solo las compras pagadas (sin créditos de regalo): para el historial y las boletas."""
    return usuario.compras.filter(tipo=Compra.COMPRA)


def registrar_compra(usuario, paquete, metodo, detalle_pago):
    hoy = timezone.localdate()
    return Compra.objects.create(
        usuario=usuario, paquete=paquete,
        vence=sumar_meses(hoy, paquete.vigencia_meses),
        nombre_paquete=paquete.nombre, creditos=paquete.creditos, precio_pagado=paquete.precio,
        sesiones_nutricion=paquete.sesiones_nutricion, sesiones_masaje=paquete.sesiones_masaje,
        incluye_circle=paquete.incluye_circle,
        metodo=metodo, detalle_pago=detalle_pago,
        numero_operacion=f'{random.randint(0, 999999):06d}',
    )
