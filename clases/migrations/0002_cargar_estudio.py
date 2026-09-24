"""
Datos iniciales del estudio: 3 salas, 4 disciplinas, el equipo y la semana tipo.

Equipo según el Plan RRHH del Excel: 1 coordinador fitness + 6 entrenadores,
2 nutricionistas y 1 masajista. Los nombres del equipo de clases son de EJEMPLO
(reggaetoneros, en broma): cambiarlos antes de presentar el prototipo.

Semana tipo (3 salas en paralelo = 156 clases por semana, como el Excel):
- Lunes a viernes: 6:30, 7:30, 8:30, 9:45, 11:00, 18:00, 19:00 y 20:00
- Sábados: 7:30, 8:45, 10:00, 11:15, 12:30, 15:00, 16:15 y 17:30
- Domingos: 8:00, 9:15, 10:30 y 11:45
Todo se puede editar después en el panel de administración.
"""
import datetime

from django.db import migrations

SALAS = ['Sala Calma', 'Sala Fuerza', 'Sala Ritmo']

DISCIPLINAS = [
    ('Pilates', 'pilates', 'Sala Calma', 'Postura, fuerza de centro y flexibilidad, con movimientos controlados.'),
    ('Yoga', 'yoga', 'Sala Calma', 'Equilibrio, respiración y movilidad para soltar el estrés del día.'),
    ('Pesas', 'pesas', 'Sala Fuerza', 'Fuerza y masa muscular con progresión guiada, clave para la salud ósea.'),
    ('Zumba', 'zumba', 'Sala Ritmo', 'Baile y cardio con música que reconoces, sin coreografías imposibles.'),
]

# (nombre, área, rol, disciplinas, frase)
EQUIPO = [
    ('Wisin', 'instruccion', 'Coordinación fitness · Pilates y Pesas', ['pilates', 'pesas'],
     'Coordino al equipo para que cada clase se adapte a ti.'),
    ('Karol G', 'instruccion', 'Pilates y Yoga', ['pilates', 'yoga'],
     'Te ayudo a ganar fuerza de centro y una mejor postura, a tu ritmo.'),
    ('Ivy Queen', 'instruccion', 'Pilates y Yoga', ['pilates', 'yoga'],
     'Respiración, equilibrio y movilidad para soltar el estrés del día.'),
    ('Daddy Yankee', 'instruccion', 'Pesas', ['pesas'],
     'La fuerza es tu mejor aliada para cuidar tus huesos y tu energía.'),
    ('Don Omar', 'instruccion', 'Pesas', ['pesas'],
     'Progresamos paso a paso, con buena técnica y sin prisa.'),
    ('Bad Bunny', 'instruccion', 'Zumba', ['zumba'],
     'Baile y cardio con música que conoces, sin coreografías imposibles.'),
    ('Nicky Jam', 'instruccion', 'Zumba', ['zumba'],
     'Aquí se viene a disfrutar: el ritmo lo pones tú.'),
    ('Lic. Andrea Ríos', 'nutricion', 'Nutrición', [],
     'Planes realistas que se adaptan a tu vida, no al revés.'),
    ('Lic. Carmen Salazar', 'nutricion', 'Nutrición', [],
     'Te acompaño a comer mejor, sin dietas imposibles.'),
    ('Rosa Quispe', 'masajes', 'Masajes', [],
     'Descarga muscular y relajación para recuperarte mejor.'),
]

HORAS = {
    'semana': ['06:30', '07:30', '08:30', '09:45', '11:00', '18:00', '19:00', '20:00'],
    'sabado': ['07:30', '08:45', '10:00', '11:15', '12:30', '15:00', '16:15', '17:30'],
    'domingo': ['08:00', '09:15', '10:30', '11:45'],
}
NIVELES = ['suave', 'media', 'activa']


def instructor_para(dia, i, sala):
    """Reparte el equipo sin que nadie tenga dos clases a la misma hora."""
    manana = i < 4
    if dia == 6:  # domingo
        return {'Sala Calma': 'Karol G', 'Sala Fuerza': 'Wisin', 'Sala Ritmo': 'Nicky Jam'}[sala]
    if dia == 5:  # sábado
        return {'Sala Calma': 'Wisin' if manana else 'Ivy Queen',
                'Sala Fuerza': 'Daddy Yankee' if manana else 'Don Omar',
                'Sala Ritmo': 'Bad Bunny' if manana else 'Nicky Jam'}[sala]
    return {'Sala Calma': 'Karol G' if manana else 'Ivy Queen',
            'Sala Fuerza': 'Daddy Yankee' if manana else 'Don Omar',
            'Sala Ritmo': 'Bad Bunny' if manana else 'Nicky Jam'}[sala]


def cargar(apps, schema_editor):
    Sala = apps.get_model('clases', 'Sala')
    Disciplina = apps.get_model('clases', 'Disciplina')
    Profesional = apps.get_model('clases', 'Profesional')
    HorarioBase = apps.get_model('clases', 'HorarioBase')

    salas = {n: Sala.objects.create(nombre=n, orden=i) for i, n in enumerate(SALAS)}
    disciplinas = {}
    for i, (nombre, slug, sala, frase) in enumerate(DISCIPLINAS):
        disciplinas[slug] = Disciplina.objects.create(nombre=nombre, slug=slug, sala=salas[sala], frase=frase, orden=i)
    equipo = {}
    for i, (nombre, area, rol, slugs, frase) in enumerate(EQUIPO):
        p = Profesional.objects.create(nombre=nombre, area=area, rol=rol, frase=frase, orden=i)
        p.disciplinas.set([disciplinas[s] for s in slugs])
        equipo[nombre] = p

    for dia in range(7):
        horas = HORAS['domingo'] if dia == 6 else HORAS['sabado'] if dia == 5 else HORAS['semana']
        for i, hora in enumerate(horas):
            for s, sala in enumerate(SALAS):
                instructor = instructor_para(dia, i, sala)
                if sala == 'Sala Calma':
                    # Pilates y Yoga se alternan; el coordinador solo da Pilates
                    slug = 'pilates' if instructor == 'Wisin' or (i + dia) % 2 == 0 else 'yoga'
                elif sala == 'Sala Fuerza':
                    slug = 'pesas'
                else:
                    slug = 'zumba'
                HorarioBase.objects.create(
                    dia_semana=dia, hora=datetime.time.fromisoformat(hora), sala=salas[sala],
                    disciplina=disciplinas[slug], instructor=equipo[instructor],
                    nivel=NIVELES[(i + s + dia) % 3],
                )


def borrar(apps, schema_editor):
    for modelo in ['HorarioBase', 'Profesional', 'Disciplina', 'Sala']:
        apps.get_model('clases', modelo).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar, borrar),
    ]
