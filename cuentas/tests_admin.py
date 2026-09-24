"""Ajuste manual de puntos y botón "Salir sin guardar" en el panel."""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from compras.models import Compra, creditos_disponibles, registrar_compra
from notificaciones.models import Notificacion
from paquetes.models import Paquete

Usuario = get_user_model()


class AjusteDeCreditosTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave-de-prueba', nombre='Admin', apellido='Atempo')
        self.maria = Usuario.objects.create_user('maria@correo.pe', 'Ritmo-propio-2026', nombre='María',
                                                 apellido='Salas', celular='987654321', dni='45678912')
        registrar_compra(self.maria, Paquete.objects.get(slug='atempo-5'), 'yape', '')
        self.client.force_login(self.admin)
        self.url = f'/admin/cuentas/usuario/{self.maria.pk}/change/'

    def guardar(self, **ajuste):
        """Envía el formulario de la ficha tal como está, más el ajuste."""
        pagina = self.client.get(self.url)
        form = pagina.context['adminform'].form
        datos = {}
        for nombre, campo in form.fields.items():
            valor = form.initial.get(nombre, campo.initial)
            if valor is None or nombre in ('password',):
                continue
            if isinstance(valor, (list, tuple)):
                datos[nombre] = [getattr(v, 'pk', v) for v in valor]
            elif isinstance(valor, bool):
                if valor:
                    datos[nombre] = 'on'
            else:
                datos[nombre] = getattr(valor, 'pk', valor)
        # formulario de los registros de puntos (solo lectura: no se envía ninguna fila)
        for prefijo in [f.formset.prefix for f in pagina.context['inline_admin_formsets']]:
            datos.update({f'{prefijo}-TOTAL_FORMS': '0', f'{prefijo}-INITIAL_FORMS': '0',
                          f'{prefijo}-MIN_NUM_FORMS': '0', f'{prefijo}-MAX_NUM_FORMS': '1000'})
        datos.update(ajuste)
        return self.client.post(self.url, datos, follow=True)

    def test_la_ficha_muestra_creditos_y_detalle(self):
        pagina = self.client.get(self.url)
        self.assertContains(pagina, 'Ajustar puntos')
        self.assertContains(pagina, 'Detalle de puntos')
        self.assertContains(pagina, 'Salir sin guardar')

    def test_sumar_creditos(self):
        respuesta = self.guardar(ajuste_creditos='2', ajuste_motivo='compensación')
        self.assertContains(respuesta, 'Se sumaron 2 puntos')
        self.assertEqual(creditos_disponibles(self.maria), 7)
        ajuste = self.maria.compras.get(tipo=Compra.AJUSTE)
        self.assertEqual(ajuste.precio_pagado, 0)
        aviso = self.maria.notificaciones.get(tipo=Notificacion.AJUSTE_CREDITOS)
        self.assertIn('El estudio agregó 2 puntos', aviso.texto)
        self.assertIn('compensación', aviso.texto)

    def test_quitar_creditos(self):
        respuesta = self.guardar(ajuste_creditos='-1')
        self.assertContains(respuesta, 'Se quitó 1 punto')
        self.assertEqual(creditos_disponibles(self.maria), 4)

    def test_no_se_pueden_quitar_mas_de_los_que_tiene(self):
        respuesta = self.guardar(ajuste_creditos='-9')
        self.assertContains(respuesta, 'solo tiene 5 puntos disponibles')
        self.assertEqual(creditos_disponibles(self.maria), 5)

    def test_vigencia_elegida(self):
        vence = timezone.localdate() + datetime.timedelta(days=10)
        self.guardar(ajuste_creditos='1', ajuste_vence=vence.isoformat())
        self.assertEqual(self.maria.compras.get(tipo=Compra.AJUSTE).vence, vence)

    def test_salir_sin_guardar_en_otras_secciones(self):
        paquete = Paquete.objects.first()
        self.assertContains(self.client.get(f'/admin/paquetes/paquete/{paquete.pk}/change/'), 'Salir sin guardar')
