from urllib.parse import quote_plus

from django.views.generic import TemplateView

# Dirección de ejemplo del local (se actualizará cuando elijan el local).
DIRECCION = 'Av. Petit Thouars, San Isidro, Lima'


def iniciales(nombre):
    """'Lic. Andrea Ríos' -> 'AR'. Ignora títulos como 'Lic.'."""
    palabras = [p for p in nombre.split() if not p.endswith('.')]
    return (palabras[0][0] + palabras[-1][0]).upper()


# Perfiles de ejemplo del prototipo (personas ficticias).
EQUIPO = [
    {'nombre': 'Carla Mendoza', 'rol': 'Pilates',
     'frase': 'Te ayudo a ganar fuerza de centro y una mejor postura, a tu ritmo.'},
    {'nombre': 'Mariana Solís', 'rol': 'Yoga',
     'frase': 'Respiración, equilibrio y movilidad para soltar el estrés del día.'},
    {'nombre': 'Diego Salas', 'rol': 'Pesas',
     'frase': 'La fuerza es tu mejor aliada para cuidar tus huesos y tu energía.'},
    {'nombre': 'Vanessa Luna', 'rol': 'Zumba',
     'frase': 'Baile y cardio con música que conoces, sin coreografías imposibles.'},
    {'nombre': 'Lic. Andrea Ríos', 'rol': 'Nutrición',
     'frase': 'Planes realistas que se adaptan a tu vida, no al revés.'},
    {'nombre': 'Rosa Quispe', 'rol': 'Masajes',
     'frase': 'Descarga muscular y relajación para recuperarte mejor.'},
]

# Integrantes del proyecto de tesis. Las áreas son provisionales.
FUNDADORES = [
    {'nombre': 'Grecia Ballesteros', 'rol': 'Marketing',
     'frase': 'Quiero que cada mujer que entre a Atempo se sienta vista y representada.'},
    {'nombre': 'Sebastián Alfaro', 'rol': 'Operaciones',
     'frase': 'Me encargo de que cada clase y cada reserva funcionen, para que tú solo te ocupes de disfrutar.'},
    {'nombre': 'Jeremy Serrano', 'rol': 'Finanzas',
     'frase': 'Trabajo para que Atempo crezca de forma sostenible y sea un espacio que dure.'},
    {'nombre': 'Lucía Sotomayor', 'rol': 'Recursos Humanos',
     'frase': 'Busco personas que enseñen con cercanía, porque el equipo es el corazón de la experiencia.'},
]

for persona in EQUIPO + FUNDADORES:
    persona['iniciales'] = iniciales(persona['nombre'])


# Disciplinas del estudio. Se reutilizarán en la página de horarios.
DISCIPLINAS = [
    {'nombre': 'Pilates', 'sala': 'Sala Calma',
     'frase': 'Postura, fuerza de centro y flexibilidad, con movimientos controlados.'},
    {'nombre': 'Yoga', 'sala': 'Sala Calma',
     'frase': 'Equilibrio, respiración y movilidad para soltar el estrés del día.'},
    {'nombre': 'Pesas', 'sala': 'Sala Fuerza',
     'frase': 'Fuerza y masa muscular con progresión guiada, clave para la salud ósea.'},
    {'nombre': 'Zumba', 'sala': 'Sala Ritmo',
     'frase': 'Baile y cardio con música que reconoces, sin coreografías imposibles.'},
]

NIVELES = ['Suave', 'Media', 'Activa']

# Imágenes de la portada principal, que cambian solas.
PORTADA = ['Clase de Pilates', 'Encuentro de Atempo Circle', 'El estudio']


class InicioView(TemplateView):
    template_name = 'paginas/inicio.html'
    extra_context = {
        'titulo': 'Estudio boutique de bienestar en San Isidro',
        'portada': PORTADA,
        'disciplinas': DISCIPLINAS,
        'niveles': NIVELES,
        'mapa_estacionamientos': 'https://www.google.com/maps/search/'
                                 + quote_plus('estacionamientos cerca de ' + DIRECCION),
    }


class NosotrosView(TemplateView):
    template_name = 'paginas/nosotros.html'
    extra_context = {
        'titulo': 'Sobre nosotros',
        'equipo': EQUIPO,
        'fundadores': FUNDADORES,
    }
