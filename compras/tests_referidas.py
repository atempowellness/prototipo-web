import datetime
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.models import generar_codigo_referida
from paquetes.models import Paquete

from .models import Compra, creditos_disponibles, registrar_compra
from .referidas import aplicar_beneficio

Usuario = get_user_model()
YAPE = {'metodo': 'yape', 'celular': '912345678', 'codigo_yape': '123456'}


def cuenta(nombre, n, **extra):
    return Usuario.objects.create_user(f'{nombre.lower()}{n}@correo.pe', 'Ritmo-propio-2026', nombre=nombre,
                                       apellido='Prueba', celular=f'9{n:08d}', dni=f'{n:08d}', **extra)


class CodigoTests(TestCase):
    def test_formato_del_codigo(self):
        self.assertRegex(generar_codigo_referida('María José'), r'^MARIA-[A-HJ-NP-Z2-9]{4}$')
        maria = cuenta('María', 1)
        self.assertRegex(maria.codigo_referida, r'^MARIA-[A-HJ-NP-Z2-9]{4}$')

    def test_codigos_unicos(self):
        codigos = {cuenta('Ana', n).codigo_referida for n in range(1, 21)}
        self.assertEqual(len(codigos), 20)


class RegistroConCodigoTests(TestCase):
    def setUp(self):
        self.maria = cuenta('María', 1)

    def datos(self, codigo):
        return {'nombre': 'Ana', 'apellido': 'Paz', 'email': 'ana@correo.pe', 'celular': '912345678',
                'dni': '12345678', 'password1': 'Ritmo-propio-2026', 'password2': 'Ritmo-propio-2026',
                'acepto_privacidad': 'on', 'codigo_referida': codigo}

    def test_codigo_en_minusculas_funciona(self):
        self.client.post(reverse('registro'), self.datos(self.maria.codigo_referida.lower()))
        self.assertEqual(Usuario.objects.get(email='ana@correo.pe').referida_por, self.maria)

    def test_codigo_inexistente(self):
        respuesta = self.client.post(reverse('registro'), self.datos('NADIE-XXXX'))
        self.assertContains(respuesta, 'No encontramos ese código')
        self.assertFalse(Usuario.objects.filter(email='ana@correo.pe').exists())

    def test_enlace_de_whatsapp_trae_el_codigo(self):
        respuesta = self.client.get(reverse('registro') + f'?codigo={self.maria.codigo_referida}')
        self.assertContains(respuesta, f'value="{self.maria.codigo_referida}"')


class BeneficioTests(TestCase):
    def setUp(self):
        self.maria = cuenta('María', 1)
        self.ana = cuenta('Ana', 2, referida_por=self.maria)

    def comprar(self, usuario, slug):
        compra = registrar_compra(usuario, Paquete.objects.get(slug=slug), 'yape', '')
        return compra, aplicar_beneficio(compra)

    def test_ambas_reciben_1_credito_con_la_primera_compra_desde_atempo_5(self):
        compra, resultado = self.comprar(self.ana, 'atempo-5')
        self.assertTrue(resultado['invitadora_recibe'])
        self.assertEqual(creditos_disponibles(self.ana), 6)
        self.assertEqual(creditos_disponibles(self.maria), 1)
        # La amiga: misma vigencia de su compra. Quien invitó: 1 mes desde hoy.
        self.assertEqual(self.ana.compras.get(tipo=Compra.REGALO).vence, compra.vence)
        regalo_maria = self.maria.compras.get(tipo=Compra.REGALO)
        self.assertEqual(regalo_maria.precio_pagado, 0)

    def test_atempo_1_no_activa_pero_no_pierde_el_beneficio(self):
        _, resultado = self.comprar(self.ana, 'atempo-1')
        self.assertIsNone(resultado)
        _, resultado = self.comprar(self.ana, 'atempo-10')
        self.assertIsNotNone(resultado)
        self.assertEqual(self.maria.compras.filter(tipo=Compra.REGALO).count(), 1)

    def test_solo_una_vez(self):
        self.comprar(self.ana, 'atempo-5')
        _, resultado = self.comprar(self.ana, 'atempo-10')
        self.assertIsNone(resultado)
        self.assertEqual(self.maria.compras.filter(tipo=Compra.REGALO).count(), 1)

    def test_tope_de_5_al_mes_para_quien_invita(self):
        for n in range(3, 9):   # 6 amigas
            amiga = cuenta('Amiga', n, referida_por=self.maria)
            _, resultado = self.comprar(amiga, 'atempo-5')
            self.assertEqual(creditos_disponibles(amiga), 6)          # la amiga siempre recibe el suyo
        self.assertFalse(resultado['invitadora_recibe'])
        self.assertEqual(self.maria.compras.filter(tipo=Compra.REGALO).count(), 5)

    def test_regalo_no_aparece_en_historial_ni_tiene_boleta(self):
        self.comprar(self.ana, 'atempo-5')
        self.client.force_login(self.maria)
        respuesta = self.client.get(reverse('cuenta'))
        self.assertContains(respuesta, '1 punto de regalo por referida')
        self.assertContains(respuesta, 'Todavía no has comprado paquetes.')
        regalo = self.maria.compras.get(tipo=Compra.REGALO)
        self.assertEqual(self.client.get(reverse('compra', args=[regalo.pk])).status_code, 404)

    def test_regalo_vencido_no_cuenta(self):
        self.comprar(self.ana, 'atempo-5')
        self.maria.compras.update(vence=timezone.localdate() - datetime.timedelta(days=1))
        self.assertEqual(creditos_disponibles(self.maria), 0)


class CodigoAlPagarTests(TestCase):
    """El campo del código solo aparece cuando la compra puede activar el beneficio."""

    def setUp(self):
        self.maria = cuenta('María', 1)
        self.ana = cuenta('Ana', 2)
        self.client.force_login(self.ana)

    def test_aparece_en_la_primera_compra_desde_atempo_5(self):
        self.assertContains(self.client.get(reverse('comprar', args=['atempo-5'])), '¿Te invitó una amiga?')

    def test_no_aparece_en_atempo_1_pero_avisa_que_se_activa_desde_atempo_5(self):
        respuesta = self.client.get(reverse('comprar', args=['atempo-1']))
        self.assertNotContains(respuesta, '¿Te invitó una amiga? Escribe')
        self.assertContains(respuesta, 'Si compras <strong class="nombre-marca">Atempo 5</strong> o un paquete mayor')
        self.assertContains(respuesta, 'href="/paquetes/atempo-5/comprar/"')

    def test_atempo_1_con_codigo_del_registro_recuerda_el_beneficio(self):
        self.ana.referida_por = self.maria
        self.ana.save()
        respuesta = self.client.get(reverse('comprar', args=['atempo-1']))
        self.assertContains(respuesta, 'Tu punto extra se activa desde Atempo 5.')
        self.assertContains(respuesta, 'Te registraste con el código de María')

    def test_sin_aviso_si_ya_compro_desde_atempo_5(self):
        registrar_compra(self.ana, Paquete.objects.get(slug='atempo-5'), 'yape', '')
        self.assertNotContains(self.client.get(reverse('comprar', args=['atempo-1'])), 'o un paquete mayor')

    def test_no_aparece_si_ya_compro_desde_atempo_5(self):
        registrar_compra(self.ana, Paquete.objects.get(slug='atempo-5'), 'yape', '')
        self.assertNotContains(self.client.get(reverse('comprar', args=['atempo-10'])), '¿Te invitó una amiga?')

    def test_no_aparece_si_ya_puso_codigo_al_registrarse_pero_avisa(self):
        self.ana.referida_por = self.maria
        self.ana.save()
        respuesta = self.client.get(reverse('comprar', args=['atempo-5']))
        self.assertNotContains(respuesta, '¿Te invitó una amiga?')
        self.assertContains(respuesta, 'se aplica el código de <strong>María</strong>')

    def test_usar_el_codigo_al_pagar(self):
        respuesta = self.client.post(reverse('comprar', args=['atempo-5']),
                                     {**YAPE, 'codigo_referida': self.maria.codigo_referida.lower()}, follow=True)
        self.assertContains(respuesta, '¡Recibiste 1 punto de regalo por venir invitada por María!')
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.referida_por, self.maria)
        self.assertEqual(creditos_disponibles(self.maria), 1)

    def test_no_puede_usar_su_propio_codigo(self):
        respuesta = self.client.post(reverse('comprar', args=['atempo-5']),
                                     {**YAPE, 'codigo_referida': self.ana.codigo_referida})
        self.assertContains(respuesta, 'Ese es tu propio código')
        self.assertFalse(Compra.objects.exists())

    def test_codigo_vacio_es_opcional(self):
        self.client.post(reverse('comprar', args=['atempo-5']), {**YAPE, 'codigo_referida': ''})
        self.assertEqual(Compra.objects.count(), 1)


class MiCuentaReferidasTests(TestCase):
    def test_tarjeta_trae_a_una_amiga(self):
        maria = cuenta('María', 1)
        ana = cuenta('Ana', 2, referida_por=maria)
        cuenta('Rosa', 3, referida_por=maria)
        compra = registrar_compra(ana, Paquete.objects.get(slug='atempo-5'), 'yape', '')
        aplicar_beneficio(compra)
        self.client.force_login(maria)
        respuesta = self.client.get(reverse('cuenta'))
        for texto in [maria.codigo_referida, 'Copiar código', 'Compartir por WhatsApp', 'https://wa.me/?text=',
                      'Ana P.', 'recibiste 1 punto', 'Rosa P.', 'esperando su primera compra',
                      'Este mes: 1 de 5']:
            self.assertContains(respuesta, texto)
