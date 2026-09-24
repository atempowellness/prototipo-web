"""Renombra los regalos por referida ya guardados: "Crédito de regalo…" → "Punto de regalo…"."""
from django.db import migrations


def renombrar(apps, schema_editor):
    Compra = apps.get_model('compras', 'Compra')
    Compra.objects.filter(nombre_paquete='Crédito de regalo por referida').update(
        nombre_paquete='Punto de regalo por referida')


def revertir(apps, schema_editor):
    Compra = apps.get_model('compras', 'Compra')
    Compra.objects.filter(nombre_paquete='Punto de regalo por referida').update(
        nombre_paquete='Crédito de regalo por referida')


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0004_textos_en_puntos'),
    ]

    operations = [
        migrations.RunPython(renombrar, revertir),
    ]
