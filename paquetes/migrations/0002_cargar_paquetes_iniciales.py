"""
Carga los 5 paquetes de lanzamiento (precios propuestos en CLAUDE.md).
Después se pueden editar desde el panel de administración.
"""
from decimal import Decimal

from django.db import migrations

PAQUETES = [
    dict(nombre='Atempo 1', creditos=1, vigencia_meses=1, precio=Decimal('65'),
         sesiones_nutricion=0, sesiones_masaje=0, incluye_circle=False,
         costo_nutricion_adicional=None, costo_masaje_adicional=None,
         frase='Ideal para probar y vivir la experiencia Atempo.', orden=1),
    dict(nombre='Atempo 5', creditos=5, vigencia_meses=1, precio=Decimal('300'),
         sesiones_nutricion=1, sesiones_masaje=0, incluye_circle=True,
         costo_nutricion_adicional=None, costo_masaje_adicional=None,
         frase='Para empezar una rutina de una o dos veces por semana.', orden=2),
    dict(nombre='Atempo 10', creditos=10, vigencia_meses=2, precio=Decimal('570'),
         sesiones_nutricion=1, sesiones_masaje=0, incluye_circle=True,
         costo_nutricion_adicional=1, costo_masaje_adicional=None,
         frase='Más tiempo para usar tus clases a tu ritmo.', orden=3),
    dict(nombre='Atempo 20', creditos=20, vigencia_meses=3, precio=Decimal('1080'),
         sesiones_nutricion=2, sesiones_masaje=1, incluye_circle=True,
         costo_nutricion_adicional=1, costo_masaje_adicional=2,
         frase='El equilibrio entre constancia, bienestar y precio.',
         etiqueta_destacado='Más popular', orden=4),
    dict(nombre='Atempo 40', creditos=40, vigencia_meses=4, precio=Decimal('2000'),
         sesiones_nutricion=4, sesiones_masaje=2, incluye_circle=True,
         costo_nutricion_adicional=1, costo_masaje_adicional=2,
         frase='Para quienes entrenan tres o más veces por semana.', orden=5),
]


def cargar(apps, schema_editor):
    Paquete = apps.get_model('paquetes', 'Paquete')
    for datos in PAQUETES:
        Paquete.objects.update_or_create(nombre=datos['nombre'], defaults=datos)


def borrar(apps, schema_editor):
    Paquete = apps.get_model('paquetes', 'Paquete')
    Paquete.objects.filter(nombre__in=[p['nombre'] for p in PAQUETES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('paquetes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar, borrar),
    ]
