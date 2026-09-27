"""Masajista de ejemplo: "De La Rose" pasa a llamarse "Young Miko" (pedido del equipo)."""
from django.db import migrations


def renombrar(apps, schema_editor):
    Profesional = apps.get_model('clases', 'Profesional')
    Profesional.objects.filter(nombre='De La Rose').update(nombre='Young Miko')


def deshacer(apps, schema_editor):
    Profesional = apps.get_model('clases', 'Profesional')
    Profesional.objects.filter(nombre='Young Miko').update(nombre='De La Rose')


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0006_asistencia'),
    ]

    operations = [
        migrations.RunPython(renombrar, deshacer),
    ]
