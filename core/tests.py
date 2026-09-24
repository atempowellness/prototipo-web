from django.test import TestCase
from django.urls import reverse

PAGINAS_EN_CONSTRUCCION = [
    'comunidad', 'privacidad', 'terminos', 'reclamaciones',
]


class MarcoComunTests(TestCase):
    def test_paginas_en_construccion_cargan(self):
        for nombre in PAGINAS_EN_CONSTRUCCION:
            with self.subTest(pagina=nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, 'Página en construcción')

    def test_marco_comun_presente(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'Prototipo de demostración')
        self.assertContains(respuesta, 'Horario del estudio')
        self.assertContains(respuesta, 'Muévete, cuídate y conecta.')
        self.assertContains(respuesta, 'Ingresar')

    def test_menu_marca_la_pagina_actual(self):
        respuesta = self.client.get(reverse('paquetes'))
        self.assertContains(respuesta, 'href="/paquetes/" aria-current="page"')


class InicioTests(TestCase):
    def test_muestra_todos_los_bloques(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.status_code, 200)
        for texto in [
            'Vuelve a tu propio ritmo.', 'Ver horarios y reservar',
            'Muévete, cuídate y conecta', 'Conoce nuestra historia',
            'Nuestras disciplinas', 'Pilates', 'Yoga', 'Pesas', 'Zumba', 'Activa',
            'Cómo funciona', 'Ahorra hasta <span class="cifra">S/ 15</span> por clase', 'Atempo Circle',
            'Preguntas frecuentes', '¿Hay estacionamiento?',
        ]:
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, 'Página en construcción')

    def test_direccion_en_el_pie_de_pagina(self):
        self.assertContains(self.client.get(reverse('inicio')), 'Av. Vía Principal 140, San Isidro, Lima')

    def test_no_menciona_el_aforo(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertNotContains(respuesta, '12 personas')

    def test_enlace_a_estacionamientos_en_google_maps(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(
            respuesta,
            'https://www.google.com/maps/search/estacionamientos+cerca+de+Av.+V%C3%ADa+Principal+140%2C+San+Isidro%2C+Lima',
        )


class NosotrosTests(TestCase):
    def test_muestra_todos_los_bloques(self):
        respuesta = self.client.get(reverse('nosotros'))
        self.assertEqual(respuesta.status_code, 200)
        for texto in [
            'Nuestra historia', '¿Por qué Atempo?', 'Muévete, cuídate y conecta',
            'Nuestro equipo', 'Misión', 'Visión', 'Propósito',
            'Quiénes fundamos Atempo', 'Ver horarios', 'Ver paquetes',
        ]:
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, 'Página en construcción')

    def test_resalta_el_nombre_de_la_marca_en_las_frases(self):
        respuesta = self.client.get(reverse('nosotros'))
        self.assertContains(
            respuesta,
            'que cada mujer que entre a <strong class="nombre-marca">Atempo</strong> se sienta',
        )

    def test_muestra_equipo_y_fundadores_con_iniciales(self):
        respuesta = self.client.get(reverse('nosotros'))
        self.assertContains(respuesta, 'Lic. María Becerra')
        self.assertContains(respuesta, '>MB<')
        self.assertContains(respuesta, 'Sebastián Alfaro')
        self.assertContains(respuesta, 'Operaciones')
