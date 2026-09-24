"""
Filtros de formato para las plantillas.

Uso:
  {% load formato %}
  {{ paquete.precio|soles }}   ->  S/ 1,060
"""
from decimal import Decimal, ROUND_HALF_UP

from django import template

register = template.Library()


@register.filter
def soles(monto):
    """Muestra un monto en soles: sin decimales si es exacto, con 2 si no."""
    monto = Decimal(monto).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if monto == monto.to_integral_value():
        return f'S/ {int(monto):,}'
    return f'S/ {monto:,.2f}'


@register.filter
def hace(momento):
    """'hace un momento', 'hace 5 minutos', 'hace 2 horas', 'ayer', 'hace 3 días' o la fecha."""
    from django.utils import timezone
    from django.utils.formats import date_format

    segundos = (timezone.now() - momento).total_seconds()
    minutos, horas, dias = int(segundos // 60), int(segundos // 3600), int(segundos // 86400)
    if minutos < 1:
        return 'hace un momento'
    if horas < 1:
        return f'hace {minutos} minuto{"s" if minutos != 1 else ""}'
    if dias < 1:
        return f'hace {horas} hora{"s" if horas != 1 else ""}'
    if dias == 1:
        return 'ayer'
    if dias < 7:
        return f'hace {dias} días'
    return date_format(timezone.localtime(momento), 'j \\d\\e F')


@register.filter
def meses(cantidad):
    """1 -> '1 mes', 3 -> '3 meses'."""
    return f'{cantidad} mes' if cantidad == 1 else f'{cantidad} meses'


@register.filter
def creditos(cantidad):
    """1 -> '1 punto', 5 -> '5 puntos'."""
    return f'{cantidad} punto' if cantidad == 1 else f'{cantidad} puntos'
