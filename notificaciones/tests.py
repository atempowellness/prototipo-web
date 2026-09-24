import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from compras.models import Compra, registrar_compra
from compras.referidas import aplicar_beneficio
from paquetes.models import Paquete

from .models import Notificacion, notificar

Usuario = get_user_model()


def cuenta(nombre, n, **extra):
    return Usuario.objects.create_user(f'{nombre.lower()}{n}@correo.pe', 'Ritmo-propio-2026', nombre=nombre,
                                       apellido='Paz', celular=f'9{n:08d}', dni=f'{n:08d}', **extra)


class CuandoSeCreanTests(TestCase):
    def test_bienvenida_y_aviso_a_quien_invito_al_registrarse(self):
        maria = cuenta('María', 1)
        self.client.post(reverse('registro'), {
            'nombre': 'Ana', 'apellido': 'Paz', 'email': 'ana@correo.pe', 'celular': '912345678',
            'dni': '12345678', 'password1': 'Ritmo-propio-2026', 'password2': 'Ritmo-propio-2026',
            'acepto_privacidad': 'on', 'codigo_referida': maria.codigo_referida})
        ana = Usuario.objects.get(email='ana@correo.pe')
        self.assertTrue(ana.notificaciones.filter(tipo=Notificacion.BIENVENIDA).exists())
        aviso = maria.notificaciones.get(tipo=Notificacion.REFERIDA_REGISTRO)
        self.assertIn('Ana P. se registró con tu código', aviso.texto)

    def test_aviso_cuando_la_amiga_compra(self):
        maria = cuenta('María', 1)
        ana = cuenta('Ana', 2, referida_por=maria)
        aplicar_beneficio(registrar_compra(ana, Paquete.objects.get(slug='atempo-5'), 'yape', ''))
        aviso = maria.notificaciones.get(tipo=Notificacion.REFERIDA_COMPRA)
        self.assertIn('Se activó tu punto de regalo: puedes usarlo hasta el', aviso.texto)
        extra = ana.notificaciones.get(tipo=Notificacion.CREDITO_EXTRA)
        self.assertIn('Se activó tu punto extra por venir invitada por María', extra.texto)

    def test_activacion_de_creditos_al_comprar(self):
        ana = cuenta('Ana', 2)
        self.client.force_login(ana)
        self.client.post(reverse('comprar', args=['atempo-10']),
                         {'metodo': 'yape', 'celular': '912345678', 'codigo_yape': '123456'})
        aviso = ana.notificaciones.get(tipo=Notificacion.CREDITOS_ACTIVADOS)
        self.assertIn('Se activaron tus 10 puntos de Atempo 10. Puedes usarlos hasta el', aviso.texto)
        self.client.post(reverse('comprar', args=['atempo-1']),
                         {'metodo': 'yape', 'celular': '912345678', 'codigo_yape': '123456'})
        self.assertTrue(ana.notificaciones.filter(texto__startswith='Se activó tu punto de Atempo 1. Puedes usarlo').exists())

    def test_vencimiento_en_singular(self):
        ana = cuenta('Ana', 2)
        compra = registrar_compra(ana, Paquete.objects.get(slug='atempo-1'), 'yape', '')
        Compra.objects.filter(pk=compra.pk).update(vence=timezone.localdate() + datetime.timedelta(days=2))
        self.client.force_login(ana)
        respuesta = self.client.get(reverse('cuenta'))
        aviso = ana.notificaciones.get(tipo=Notificacion.VENCIMIENTO)
        self.assertTrue(aviso.texto.startswith('Te queda 1 punto de tu Atempo 1 y vence el'))
        self.assertContains(respuesta, 'Tu punto está por vencer.')
        self.assertNotContains(respuesta, 'Te quedan 1')

    def test_aviso_de_tope_mensual(self):
        maria = cuenta('María', 1)
        for n in range(2, 8):
            amiga = cuenta('Amiga', n, referida_por=maria)
            aplicar_beneficio(registrar_compra(amiga, Paquete.objects.get(slug='atempo-5'), 'yape', ''))
        ultimo = maria.notificaciones.filter(tipo=Notificacion.REFERIDA_COMPRA).first()
        self.assertIn('llegaste al tope', ultimo.texto)

    def test_vencimiento_se_avisa_una_sola_vez(self):
        ana = cuenta('Ana', 2)
        compra = registrar_compra(ana, Paquete.objects.get(slug='atempo-5'), 'yape', '')
        self.client.force_login(ana)
        self.client.get(reverse('inicio'))
        self.assertFalse(ana.notificaciones.filter(tipo=Notificacion.VENCIMIENTO).exists())
        Compra.objects.filter(pk=compra.pk).update(vence=timezone.localdate() + datetime.timedelta(days=5))
        self.client.get(reverse('inicio'))
        self.client.get(reverse('paquetes'))
        self.assertEqual(ana.notificaciones.filter(tipo=Notificacion.VENCIMIENTO).count(), 1)


class CampanitaTests(TestCase):
    def setUp(self):
        self.ana = cuenta('Ana', 2)
        self.client.force_login(self.ana)
        notificar(self.ana, Notificacion.BIENVENIDA, 'Primera', '/paquetes/')
        notificar(self.ana, Notificacion.BIENVENIDA, 'Segunda')

    def test_solo_con_sesion(self):
        self.client.logout()
        self.assertNotContains(self.client.get(reverse('inicio')), 'data-campanita')

    def test_muestra_contador_y_avisos(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'data-campanita')
        self.assertContains(respuesta, 'Notificaciones: 2 sin leer')
        self.assertContains(respuesta, 'Primera')
        self.assertContains(respuesta, 'hace un momento')

    def test_maximo_10_en_el_menu(self):
        for n in range(15):
            notificar(self.ana, Notificacion.BIENVENIDA, f'Aviso número {n}')
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.content.decode().count('data-aviso'), 10)

    def test_al_abrir_se_marcan_como_leidas(self):
        respuesta = self.client.post(reverse('notificaciones_leidas'), HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json()['sin_leer'], 0)
        self.assertNotContains(self.client.get(reverse('inicio')), 'sin leer')

    def test_borrar_una(self):
        aviso = self.ana.notificaciones.get(texto='Primera')
        self.client.post(reverse('notificacion_borrar', args=[aviso.pk]), HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(self.ana.notificaciones.count(), 1)

    def test_borrar_todas_sin_javascript_vuelve_a_la_pagina(self):
        respuesta = self.client.post(reverse('notificaciones_borrar_todas'), {'next': '/paquetes/'})
        self.assertRedirects(respuesta, '/paquetes/')
        self.assertEqual(self.ana.notificaciones.count(), 0)
        self.assertContains(self.client.get(reverse('inicio')), 'No tienes notificaciones.')

    def test_no_puede_borrar_las_de_otra(self):
        maria = cuenta('María', 1)
        aviso = notificar(maria, Notificacion.BIENVENIDA, 'De María')
        self.client.post(reverse('notificacion_borrar', args=[aviso.pk]))
        self.assertTrue(Notificacion.objects.filter(pk=aviso.pk).exists())

    def test_mi_cuenta_se_muestra_con_texto_e_icono(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'class="texto-cuenta">Mi cuenta</span>')
