from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from compras.models import registrar_compra

from .models import Paquete, paquete_founding, paquetes_activos, precio_clase_suelta

Usuario = get_user_model()


def socia(n=1):
    return Usuario.objects.create_user(f'socia{n}@correo.pe', 'Ritmo-propio-2026', nombre=f'Socia{n}',
                                       apellido='Prueba', celular=f'9{n:08d}', dni=f'{n:08d}')


PAGO = {'metodo': 'yape', 'yape_celular': '987654321', 'yape_codigo': '123456'}


class FoundingMembersTests(TestCase):
    def setUp(self):
        self.founding = Paquete.objects.get(slug='founding-members')

    def test_paquete_provisional_como_atempo_20(self):
        self.assertTrue(self.founding.es_founding)
        self.assertEqual((self.founding.creditos, self.founding.precio, self.founding.precio_referencia),
                         (20, 900, 1060))
        self.assertEqual(self.founding.ventas_maximas, 100)
        # No cuenta como paquete normal (ni para el ahorro ni para la clase suelta)
        self.assertNotIn(self.founding, paquetes_activos())
        self.assertEqual(precio_clase_suelta(), 65)

    def test_pagina_paquetes_muestra_la_preventa(self):
        respuesta = self.client.get(reverse('paquetes'))
        for texto in ['Preventa · Edición limitada', 'Quedan <strong class="cifra">100</strong> de 100 cupos',
                      'S/ 1,060</s>', 'Precio Founding Member', 'Quiero ser Founding Member']:
            self.assertContains(respuesta, texto)

    def test_solo_como_primera_compra(self):
        ana = socia()
        registrar_compra(ana, Paquete.objects.get(slug='atempo-5'), 'yape', '')
        self.client.force_login(ana)
        self.assertContains(self.client.get(reverse('paquetes')), 'Solo disponible como primera compra.')
        respuesta = self.client.get(reverse('comprar', args=['founding-members']), follow=True)
        self.assertContains(respuesta, 'es solo para la primera compra')

    def test_compra_insignia_y_numero(self):
        ana, bea = socia(1), socia(2)
        registrar_compra(ana, self.founding, 'yape', '')
        registrar_compra(bea, self.founding, 'yape', '')
        self.assertEqual((ana.numero_founding, bea.numero_founding), (1, 2))
        self.client.force_login(bea)
        cuenta = self.client.get(reverse('cuenta'))
        self.assertContains(cuenta, 'class="tarjeta-founding"')
        self.assertContains(cuenta, 'Socia fundadora <span class="cifra">N.° 2 de 100</span>')
        self.assertContains(cuenta, 'boton-cuenta-founding')
        self.assertContains(cuenta, 'class="insignia-menu-texto">Founding</span>')
        self.founding.refresh_from_db()
        self.assertEqual(self.founding.quedan, 98)

    def test_panel_muestra_la_preventa_solo_en_founding(self):
        admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave', nombre='Admin', apellido='Atempo')
        self.client.force_login(admin)
        ficha = self.client.get(f'/admin/paquetes/paquete/{self.founding.pk}/change/')
        self.assertContains(ficha, 'Preventa Founding Members')
        self.assertContains(ficha, 'name="ventas_maximas"')
        self.assertNotContains(ficha, 'collapse')
        otro = Paquete.objects.get(slug='atempo-10')
        self.assertNotContains(self.client.get(f'/admin/paquetes/paquete/{otro.pk}/change/'), 'name="ventas_maximas"')
        self.assertContains(self.client.get('/admin/paquetes/paquete/'), '0 de 100 (quedan 100)')

    def test_desaparece_al_agotarse(self):
        Paquete.objects.filter(pk=self.founding.pk).update(ventas_maximas=1)
        registrar_compra(socia(1), self.founding, 'yape', '')
        self.assertIsNone(paquete_founding())
        self.assertNotContains(self.client.get(reverse('paquetes')), 'Quiero ser Founding Member')
        self.client.force_login(socia(2))
        respuesta = self.client.get(reverse('comprar', args=['founding-members']), follow=True)
        self.assertContains(respuesta, 'ya se agotó')

    def test_aviso_antes_de_gastar_la_primera_compra_en_otro_paquete(self):
        self.client.force_login(socia())
        respuesta = self.client.get(reverse('comprar', args=['atempo-10']))
        self.assertContains(respuesta, 'Tu primera compra puede ser Founding Members.')
        pago = self.client.get(reverse('comprar', args=['founding-members']))
        self.assertContains(pago, 'Descuento por Founding Member')
        self.assertNotContains(pago, 'Tu primera compra puede ser Founding Members.')
