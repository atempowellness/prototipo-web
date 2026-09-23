from django.test import TestCase
from django.urls import reverse

PAGINAS_EN_CONSTRUCCION = [
    'inicio', 'horarios', 'paquetes', 'bienestar', 'comunidad',
    'cuenta', 'registro', 'ingresar',
    'privacidad', 'terminos', 'reclamaciones',
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

    def test_muestra_equipo_y_fundadores_con_iniciales(self):
        respuesta = self.client.get(reverse('nosotros'))
        self.assertContains(respuesta, 'Lic. Andrea Ríos')
        self.assertContains(respuesta, '>AR<')
        self.assertContains(respuesta, 'Sebastián Alfaro')
        self.assertContains(respuesta, 'Operaciones')
