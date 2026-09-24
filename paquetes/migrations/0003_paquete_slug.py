"""
Agrega la "dirección web" de cada paquete (por ejemplo "atempo-10"),
usada en la página de compra /paquetes/atempo-10/comprar/.
"""
from django.db import migrations, models
from django.utils.text import slugify


def llenar_slugs(apps, schema_editor):
    Paquete = apps.get_model('paquetes', 'Paquete')
    for paquete in Paquete.objects.all():
        paquete.slug = slugify(paquete.nombre)
        paquete.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('paquetes', '0002_cargar_paquetes_iniciales'),
    ]

    operations = [
        migrations.AddField(
            model_name='paquete',
            name='slug',
            field=models.SlugField(default='', max_length=40, verbose_name='dirección web'),
            preserve_default=False,
        ),
        migrations.RunPython(llenar_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='paquete',
            name='slug',
            field=models.SlugField(
                help_text='Se usa en la dirección de compra, por ejemplo "atempo-10" → /paquetes/atempo-10/comprar/.',
                max_length=40, unique=True, verbose_name='dirección web'),
        ),
    ]
