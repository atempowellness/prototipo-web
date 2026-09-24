"""
Programa de referidas: código personal de cada cuenta (por ejemplo MARIA-7K3Q)
y a quién la invitó. A las cuentas que ya existían se les genera su código.
"""
import random
import re
import unicodedata

import django.db.models.deletion
from django.db import migrations, models

CARACTERES_CODIGO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generar_codigos(apps, schema_editor):
    Usuario = apps.get_model('cuentas', 'Usuario')
    usados = set()
    for usuario in Usuario.objects.all():
        sin_tildes = unicodedata.normalize('NFKD', usuario.nombre or '').encode('ascii', 'ignore').decode()
        palabras = re.findall(r'[A-Za-z]+', sin_tildes)
        base = (palabras[0] if palabras else 'ATEMPO').upper()[:10]
        codigo = None
        while codigo is None or codigo in usados:
            codigo = f'{base}-' + ''.join(random.choices(CARACTERES_CODIGO, k=4))
        usados.add(codigo)
        usuario.codigo_referida = codigo
        usuario.save(update_fields=['codigo_referida'])


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0002_nombre_en_panel'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='codigo_referida',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='código de referida'),
            preserve_default=False,
        ),
        migrations.RunPython(generar_codigos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='usuario',
            name='codigo_referida',
            field=models.CharField(blank=True, help_text='Su código personal para invitar amigas. Se crea solo.',
                                   max_length=16, unique=True, verbose_name='código de referida'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='referida_por',
            field=models.ForeignKey(blank=True, help_text='Quién la invitó. Cada cuenta puede usar un solo código.',
                                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='invitadas', to='cuentas.usuario', verbose_name='invitada por'),
        ),
    ]
