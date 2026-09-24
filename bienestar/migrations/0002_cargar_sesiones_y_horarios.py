"""
Tipos de sesión y horarios de atención iniciales (editables en el panel).

Según el Plan RRHH del Excel: nutricionistas y masajista trabajan 5 días, 8 horas.
- Nutricionista 1 (la primera por orden): lunes a viernes, 8:00–12:00 y 16:00–20:00
- Nutricionista 2: martes a sábado, 9:00–13:00 y 15:00–19:00
- Masajista: lunes a viernes, 10:00–14:00 y 16:00–20:00
"""
import datetime

from django.db import migrations

TIPOS = [
    ('nutricion', 'Evaluación y plan personalizado', 45, True, 0),
    ('nutricion', 'Seguimiento', 30, False, 1),
    ('masajes', 'Descarga muscular', 50, False, 0),
    ('masajes', 'Relajante', 50, False, 1),
]

# (área, posición entre las de esa área, días, bloques)
HORARIOS = [
    ('nutricion', 0, [0, 1, 2, 3, 4], [('08:00', '12:00'), ('16:00', '20:00')]),
    ('nutricion', 1, [1, 2, 3, 4, 5], [('09:00', '13:00'), ('15:00', '19:00')]),
    ('masajes', 0, [0, 1, 2, 3, 4], [('10:00', '14:00'), ('16:00', '20:00')]),
]


def cargar(apps, schema_editor):
    TipoSesion = apps.get_model('bienestar', 'TipoSesion')
    HorarioAtencion = apps.get_model('bienestar', 'HorarioAtencion')
    Profesional = apps.get_model('clases', 'Profesional')

    for servicio, nombre, minutos, ficha, orden in TIPOS:
        TipoSesion.objects.create(servicio=servicio, nombre=nombre, duracion_minutos=minutos,
                                  pide_ficha=ficha, orden=orden)

    for area, posicion, dias, bloques in HORARIOS:
        profesionales = list(Profesional.objects.filter(area=area).order_by('orden', 'nombre'))
        if len(profesionales) <= posicion:
            continue
        for dia in dias:
            for desde, hasta in bloques:
                HorarioAtencion.objects.create(
                    profesional=profesionales[posicion], dia_semana=dia,
                    desde=datetime.time.fromisoformat(desde), hasta=datetime.time.fromisoformat(hasta))


def borrar(apps, schema_editor):
    apps.get_model('bienestar', 'HorarioAtencion').objects.all().delete()
    apps.get_model('bienestar', 'TipoSesion').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('bienestar', '0001_initial'),
        ('clases', '0003_renombrar_equipo'),
    ]

    operations = [
        migrations.RunPython(cargar, borrar),
    ]
