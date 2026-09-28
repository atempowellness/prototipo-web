import datetime
from urllib.parse import quote_plus

from django.utils import timezone
from django.views.generic import TemplateView

from clases.models import NIVELES, Clase, Disciplina, Profesional
from paquetes.models import ahorro_maximo_por_clase, paquetes_activos, precio_clase_suelta

# Datos de la empresa (DE EJEMPLO). Es el único lugar donde están escritos: los usan
# el pie de página, la boleta, las páginas legales y el mapa de estacionamientos.
DIRECCION = 'Av. Vía Principal 140, San Isidro, Lima'   # referencia del Plan de operaciones del Excel
RAZON_SOCIAL = 'Atempo Wellness S.A.C.'
RUC = '20000000000'
CORREO = 'hola@atempo.pe'
WHATSAPP = '+51 900 000 000'

PROXIMAS_CLASES_EN_INICIO = 6


def iniciales(nombre):
    """'Sebastián Alfaro' -> 'SA'. Ignora títulos como 'Lic.'."""
    palabras = [p for p in nombre.split() if not p.endswith('.')]
    return (palabras[0][0] + palabras[-1][0]).upper()


# Integrantes del proyecto de tesis. Las áreas son provisionales.
# (El equipo del estudio se edita en el panel: Clases y horarios → Profesionales).
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

for persona in FUNDADORES:
    persona['iniciales'] = iniciales(persona['nombre'])

# Imágenes de la portada principal, que cambian solas: (descripción, archivo en static/).
# Las fotos originales están en referencias/Imágenes; aquí se usan copias optimizadas en JPG.
PORTADA = [
    ('Clase de Pilates', 'img/fotos/portada-pilates.jpg'),
    ('Encuentro de Atempo Circle', 'img/fotos/portada-circle.jpg'),
    ('El estudio', 'img/fotos/el-estudio.jpg'),
]
# Foto de cada disciplina en Inicio (según su dirección web en el panel). Sin foto, se ve el recuadro provisional.
FOTOS_DISCIPLINAS = {'pilates': 'img/fotos/disciplina-pilates.jpg', 'yoga': 'img/fotos/disciplina-yoga.jpg',
                     'pesas': 'img/fotos/disciplina-pesas.jpg', 'zumba': 'img/fotos/disciplina-zumba.jpg'}


def proximas_clases_con_cupo(cantidad=PROXIMAS_CLASES_EN_INICIO):
    """Las siguientes clases (hoy y mañana) que todavía tienen cupo real."""
    ahora = timezone.now()
    clases = (Clase.objects.filter(inicio__gt=ahora, inicio__lt=ahora + datetime.timedelta(days=2), cancelada=False)
              .select_related('sala', 'disciplina', 'instructor'))
    return [c for c in clases if c.cupos() > 0][:cantidad]


class InicioView(TemplateView):
    template_name = 'paginas/inicio.html'
    extra_context = {
        'titulo': 'Estudio boutique de bienestar en San Isidro',
        'portada': PORTADA,
        'mapa_estacionamientos': 'https://www.google.com/maps/search/'
                                 + quote_plus('estacionamientos cerca de ' + DIRECCION),
    }

    def get_context_data(self, **kwargs):
        from clases.views import asegurar_clases

        contexto = super().get_context_data(**kwargs)
        # Precios y vigencias salen de los paquetes del panel de administración
        contexto['precio_clase_suelta'] = precio_clase_suelta()
        contexto['ahorro_maximo'] = ahorro_maximo_por_clase()
        # Vigencias agrupadas: [(1, ['Atempo 1', 'Atempo 5']), (2, ['Atempo 10']), ...]
        vigencias = {}
        for paquete in paquetes_activos():
            vigencias.setdefault(paquete.vigencia_meses, []).append(paquete.nombre)
        contexto['vigencias'] = sorted(vigencias.items())
        # Disciplinas y próximas clases salen del panel (Clases y horarios)
        asegurar_clases()
        contexto['disciplinas'] = list(Disciplina.objects.select_related('sala'))
        for disciplina in contexto['disciplinas']:
            disciplina.foto = FOTOS_DISCIPLINAS.get(disciplina.slug)
        contexto['niveles'] = [nombre for _, nombre in NIVELES]
        contexto['proximas_clases'] = proximas_clases_con_cupo()
        # Próximos encuentros de Atempo Circle (panel → Comunidad)
        from comunidad.servicios import ENCUENTROS_EN_INICIO, asegurar_encuentros_de_ejemplo, proximos_encuentros
        asegurar_encuentros_de_ejemplo()
        contexto['proximos_encuentros'] = proximos_encuentros().filter(cancelado=False)[:ENCUENTROS_EN_INICIO]
        contexto['hoy'] = timezone.localdate()
        return contexto


TANDAS_DEL_MURO = 10          # el agradecimiento a las fundadoras rota en 10 tandas iguales
MINIMO_POR_TANDA = 2          # con pocas fundadoras, nunca de a una


def repartir_en_tandas(nombres, tandas=TANDAS_DEL_MURO, minimo=MINIMO_POR_TANDA):
    """Reparte en tandas lo más parejas posible: 63 nombres -> 3 tandas de 7 y 7 de 6."""
    if not nombres:
        return []
    cantidad = max(1, min(tandas, len(nombres) // minimo))
    base, sobran = divmod(len(nombres), cantidad)
    resultado, inicio = [], 0
    for i in range(cantidad):
        fin = inicio + base + (1 if i < sobran else 0)
        resultado.append(nombres[inicio:fin])
        inicio = fin
    return resultado


class NosotrosView(TemplateView):
    template_name = 'paginas/nosotros.html'

    def get_context_data(self, **kwargs):
        from paquetes.models import fundadoras_del_muro

        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = 'Sobre nosotros'
        contexto['equipo'] = Profesional.objects.filter(activo=True)
        contexto['fundadores'] = FUNDADORES
        # Agradecimiento a las Founding Members (solo las que aceptaron aparecer)
        total, visibles = fundadoras_del_muro()
        contexto['fundadoras_total'] = total                        # todas, aparezcan o no
        contexto['fundadoras_ocultas'] = total - len(visibles)
        contexto['tandas_fundadoras'] = repartir_en_tandas(visibles)
        return contexto
