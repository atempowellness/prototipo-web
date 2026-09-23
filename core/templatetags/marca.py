"""
Filtro para resaltar el nombre de la marca y de los planes en textos que
vienen de datos (por ejemplo, las frases del equipo en core/views.py).

Uso en una plantilla:
  {% load marca %}
  {{ persona.frase|marca }}
"""
import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

# "Atempo", "Atempo Wellness", "Atempo Circle" y los planes "Atempo 1" a "Atempo 40"
NOMBRE_MARCA = re.compile(r'\bAtempo(?: Wellness| Circle| \d+)?\b')


@register.filter
def marca(texto):
    seguro = conditional_escape(texto)
    return mark_safe(NOMBRE_MARCA.sub(
        lambda m: f'<strong class="nombre-marca">{m.group(0)}</strong>', seguro
    ))
