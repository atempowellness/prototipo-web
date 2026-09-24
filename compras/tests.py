import datetime
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from paquetes.models import Paquete

from .models import (Compra, creditos_disponibles, registrar_compra, sumar_meses, tiene_atempo_circle,
                     usar_credito)

Usuario = get_user_model()
TARJETA_OK = {'metodo': 'tarjeta', 'tarjeta_numero': '4111 1111 1111 1111', 'tarjeta_vence': '12/29', 'tarjeta_cvv': '123'}


def crear_maria():
    return Usuario.objects.create_user('maria@correo.pe', 'Ritmo-propio-2026', nombre='María', apellido='Salas',
                                       celular='987654321', dni='45678912')


def paquete(nombre):
    return Paquete.objects.get(nombre=nombre)


class VigenciaTests(TestCase):
    def test_sumar_meses(self):
        self.assertEqual(sumar_meses(datetime.date(2026, 9, 23), 2), datetime.date(2026, 11, 23))
        self.assertEqual(sumar_meses(datetime.date(2027, 1, 31), 1), datetime.date(2027, 2, 28))
        self.assertEqual(sumar_meses(datetime.date(2026, 11, 30), 3), datetime.date(2027, 2, 28))


class CreditosTests(TestCase):
    def setUp(self):
        self.maria = crear_maria()

    def test_cada_compra_tiene_su_vigencia_y_se_usa_primero_la_que_vence_antes(self):
        diez = registrar_compra(self.maria, paquete('Atempo 10'), 'yape', '')   # vence en 2 meses
        cinco = registrar_compra(self.maria, paquete('Atempo 5'), 'yape', '')   # vence en 1 mes
        self.assertEqual(creditos_disponibles(self.maria), 15)
        usada = usar_credito(self.maria)
        self.assertEqual(usada.pk, cinco.pk)
        self.assertEqual(creditos_disponibles(self.maria), 14)
        diez.refresh_from_db()
        self.assertEqual(diez.creditos_usados, 0)

    def test_creditos_vencidos_no_se_usan(self):
        compra = registrar_compra(self.maria, paquete('Atempo 5'), 'yape', '')
        Compra.objects.filter(pk=compra.pk).update(vence=timezone.localdate() - datetime.timedelta(days=1))
        self.assertEqual(creditos_disponibles(self.maria), 0)
        self.assertIsNone(usar_credito(self.maria))

    def test_sin_creditos_no_descuenta(self):
        registrar_compra(self.maria, paquete('Atempo 1'), 'plin', '')
        self.assertIsNotNone(usar_credito(self.maria))
        self.assertIsNone(usar_credito(self.maria))

    def test_atempo_circle_desde_atempo_5(self):
        registrar_compra(self.maria, paquete('Atempo 1'), 'plin', '')
        self.assertFalse(tiene_atempo_circle(self.maria))
        registrar_compra(self.maria, paquete('Atempo 5'), 'plin', '')
        self.assertTrue(tiene_atempo_circle(self.maria))

    def test_guarda_el_precio_pagado_aunque_cambie_el_paquete(self):
        compra = registrar_compra(self.maria, paquete('Atempo 10'), 'yape', '')
        Paquete.objects.filter(nombre='Atempo 10').update(precio=Decimal(600))
        compra.refresh_from_db()
        self.assertEqual(compra.precio_pagado, Decimal(570))

    def test_boleta_igv(self):
        compra = registrar_compra(self.maria, paquete('Atempo 20'), 'tarjeta', '')
        self.assertEqual(compra.subtotal, Decimal('915.25'))
        self.assertEqual(compra.igv, Decimal('164.75'))
        self.assertEqual(compra.numero_boleta, f'B001-{compra.pk:08d}')


class PaginaDePagoTests(TestCase):
    def setUp(self):
        self.maria = crear_maria()
        self.url = reverse('comprar', args=['atempo-10'])

    def test_sin_sesion_pide_ingresar_y_vuelve_al_pago(self):
        respuesta = self.client.get(self.url)
        self.assertRedirects(respuesta, reverse('ingresar') + '?next=' + self.url)
        # En Paquetes, "Comprar" lleva a ingresar y luego directo al pago
        paquetes = self.client.get(reverse('paquetes'))
        self.assertContains(paquetes, '?next=/paquetes/atempo-10/comprar/')

    def test_muestra_resumen_y_metodos(self):
        self.client.force_login(self.maria)
        respuesta = self.client.get(self.url)
        for texto in ['Comprar', 'Atempo 10', 'S/ 570', 'Tarjeta', 'Yape', 'Plin',
                      '¿Dónde encuentro el código de aprobación?', 'Completar con datos de prueba', 'Pago simulado']:
            self.assertContains(respuesta, texto)

    def test_pago_con_tarjeta_crea_la_compra_y_muestra_la_confirmacion(self):
        self.client.force_login(self.maria)
        respuesta = self.client.post(self.url, TARJETA_OK, follow=True)
        compra = Compra.objects.get()
        self.assertEqual(compra.detalle_pago, 'Tarjeta terminada en 1111')
        self.assertEqual(compra.vence, sumar_meses(timezone.localdate(), 2))
        for texto in ['¡Compra confirmada!', 'Ya tienes <strong>10 créditos disponibles</strong>',
                      'Boleta de venta electrónica', compra.numero_boleta, '45678912', 'IGV (18 %)',
                      'También te enviamos la boleta a']:
            self.assertContains(respuesta, texto)

    def test_nunca_guarda_el_numero_completo_de_la_tarjeta(self):
        self.client.force_login(self.maria)
        self.client.post(self.url, TARJETA_OK)
        compra = Compra.objects.get()
        valores = ' '.join(str(getattr(compra, campo.name)) for campo in Compra._meta.fields)
        self.assertNotIn('4111111111111111', valores.replace(' ', ''))

    def test_tarjeta_terminada_en_0000_es_rechazada(self):
        self.client.force_login(self.maria)
        respuesta = self.client.post(self.url, {**TARJETA_OK, 'tarjeta_numero': '4111 1111 1111 0000'})
        self.assertContains(respuesta, 'Tu banco rechazó el pago')
        self.assertFalse(Compra.objects.exists())

    def test_errores_de_tarjeta(self):
        self.client.force_login(self.maria)
        respuesta = self.client.post(self.url, {'metodo': 'tarjeta', 'tarjeta_numero': '1234',
                                                'tarjeta_vence': '01/20', 'tarjeta_cvv': '1'})
        self.assertContains(respuesta, 'debe tener 16 dígitos')
        self.assertContains(respuesta, 'Esta tarjeta ya venció')
        self.assertContains(respuesta, 'El CVV tiene 3 o 4 números')
        self.assertFalse(Compra.objects.exists())

    def test_yape_pide_celular_y_codigo(self):
        self.client.force_login(self.maria)
        respuesta = self.client.post(self.url, {'metodo': 'yape', 'celular': '123', 'codigo_yape': '12'})
        self.assertContains(respuesta, 'Ingresa un celular de 9 dígitos')
        self.assertContains(respuesta, 'El código de aprobación tiene 6 dígitos')
        self.client.post(self.url, {'metodo': 'yape', 'celular': '912 345 678', 'codigo_yape': '123456'})
        self.assertEqual(Compra.objects.get().detalle_pago, 'Yape desde el celular terminado en 678')

    def test_plin_solo_pide_celular(self):
        self.client.force_login(self.maria)
        self.client.post(self.url, {'metodo': 'plin', 'celular': '912345678'})
        self.assertEqual(Compra.objects.get().metodo, 'plin')

    def test_paquete_inactivo_no_se_puede_comprar(self):
        Paquete.objects.filter(slug='atempo-10').update(activo=False)
        self.client.force_login(self.maria)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_una_clienta_no_ve_la_boleta_de_otra(self):
        compra = registrar_compra(self.maria, paquete('Atempo 5'), 'yape', '')
        ana = Usuario.objects.create_user('ana@correo.pe', 'Ritmo-propio-2026', nombre='Ana', apellido='Paz')
        self.client.force_login(ana)
        self.assertEqual(self.client.get(reverse('compra', args=[compra.pk])).status_code, 404)


class MiCuentaConComprasTests(TestCase):
    def setUp(self):
        self.maria = crear_maria()
        self.client.force_login(self.maria)

    def test_muestra_creditos_beneficios_e_historial(self):
        registrar_compra(self.maria, paquete('Atempo 20'), 'tarjeta', 'Tarjeta terminada en 1111')
        respuesta = self.client.get(reverse('cuenta'))
        for texto in ['Créditos disponibles', '20 créditos de', 'Nutrición: <strong>2</strong>',
                      'Masajes: <strong>1</strong>', 'activo', 'Historial de compras', 'S/ 1,080', 'Ver boleta']:
            self.assertContains(respuesta, texto)

    def test_sin_compras(self):
        respuesta = self.client.get(reverse('cuenta'))
        self.assertContains(respuesta, 'Aún no tienes créditos activos.')
        self.assertContains(respuesta, 'Todavía no has comprado paquetes.')

    def test_aviso_cuando_vence_en_7_dias_o_menos(self):
        compra = registrar_compra(self.maria, paquete('Atempo 5'), 'yape', '')
        respuesta = self.client.get(reverse('cuenta'))
        self.assertNotContains(respuesta, 'Tus créditos están por vencer')
        Compra.objects.filter(pk=compra.pk).update(vence=timezone.localdate() + datetime.timedelta(days=7))
        respuesta = self.client.get(reverse('cuenta'))
        self.assertContains(respuesta, 'Tus créditos están por vencer')
        self.assertContains(respuesta, 'Ver el correo que te enviamos')

    def test_sin_aviso_si_ya_uso_todos_los_creditos(self):
        compra = registrar_compra(self.maria, paquete('Atempo 1'), 'yape', '')
        Compra.objects.filter(pk=compra.pk).update(creditos_usados=1,
                                                   vence=timezone.localdate() + datetime.timedelta(days=3))
        self.assertNotContains(self.client.get(reverse('cuenta')), 'Tus créditos están por vencer')


class PanelComprasTests(TestCase):
    def test_compras_en_el_panel(self):
        admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave-de-prueba', nombre='Admin', apellido='Atempo')
        registrar_compra(crear_maria(), paquete('Atempo 10'), 'yape', '')
        self.client.force_login(admin)
        respuesta = self.client.get('/admin/compras/compra/')
        self.assertContains(respuesta, 'Atempo 10')
        self.assertContains(respuesta, 'Eliminar pagos seleccionados')
