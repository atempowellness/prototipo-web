"""
Filtros de formato para las plantillas.

Uso:
  {% load formato %}
  {{ paquete.precio|soles }}   ->  S/ 1,080
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
def meses(cantidad):
    """1 -> '1 mes', 3 -> '3 meses'."""
    return f'{cantidad} mes' if cantidad == 1 else f'{cantidad} meses'


@register.filter
def creditos(cantidad):
    """1 -> '1 crédito', 5 -> '5 créditos'."""
    return f'{cantidad} crédito' if cantidad == 1 else f'{cantidad} créditos'
