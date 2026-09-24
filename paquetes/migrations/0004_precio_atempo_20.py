"""
Actualiza Atempo 20 a S/ 1,060 (S/ 53 por clase), según la versión nueva del Excel
y de la tesis. Solo cambia el precio si todavía está en el valor inicial (S/ 1,080),
para no pisar un precio editado a mano en el panel de administración.
"""
from decimal import Decimal

from django.db import migrations


def actualizar(apps, schema_editor):
    Paquete = apps.get_model('paquetes', 'Paquete')
    Paquete.objects.filter(nombre='Atempo 20', precio=Decimal('1080')).update(precio=Decimal('1060'))


def revertir(apps, schema_editor):
    Paquete = apps.get_model('paquetes', 'Paquete')
    Paquete.objects.filter(nombre='Atempo 20', precio=Decimal('1060')).update(precio=Decimal('1080'))


class Migration(migrations.Migration):

    dependencies = [
        ('paquetes', '0003_paquete_slug'),
    ]

    operations = [
        migrations.RunPython(actualizar, revertir),
    ]
