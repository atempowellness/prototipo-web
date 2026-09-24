"""
Cambia algunos nombres de ejemplo del equipo (siguen siendo de EJEMPLO, en broma:
cambiarlos antes de presentar el prototipo).
Solo renombra si el nombre anterior sigue igual, para no pisar cambios hechos en el panel.
"""
from django.db import migrations

CAMBIOS = [
    ('Ivy Queen', 'Becky G'),
    ('Nicky Jam', 'J Balvin'),
    ('Lic. Andrea Ríos', 'Lic. María Becerra'),
    ('Lic. Carmen Salazar', 'Lic. Nicki Nicole'),
    ('Rosa Quispe', 'De La Rose'),
]


def renombrar(apps, schema_editor):
    Profesional = apps.get_model('clases', 'Profesional')
    for antes, despues in CAMBIOS:
        Profesional.objects.filter(nombre=antes).update(nombre=despues)


def revertir(apps, schema_editor):
    Profesional = apps.get_model('clases', 'Profesional')
    for antes, despues in CAMBIOS:
        Profesional.objects.filter(nombre=despues).update(nombre=antes)


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0002_cargar_estudio'),
    ]

    operations = [
        migrations.RunPython(renombrar, revertir),
    ]
