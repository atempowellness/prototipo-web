from django.test import TestCase
from django.urls import reverse

PAGINAS = [
    'inicio', 'horarios', 'paquetes', 'bienestar', 'comunidad', 'nosotros',
    'cuenta', 'registro', 'ingresar',
    'privacidad', 'terminos', 'reclamaciones',
]


class MarcoComunTests(TestCase):
    def test_todas_las_paginas_del_mapa_cargan(self):
        for nombre in PAGINAS:
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
