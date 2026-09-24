"""
Panel: las reservas de clases y las citas tienen las mismas acciones.
- Cancelar (de verdad): devuelve el punto o la sesión y avisa a la clienta.
- Eliminar (solo pruebas): borra sin devolver ni avisar.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bienestar.models import Cita, TipoSesion
from bienestar.servicios import agendar, horas_libres, sesiones_incluidas_disponibles
from clases.models import Clase, HorarioBase, Reserva
from clases.servicios import reservar
from compras.models import creditos_disponibles, registrar_compra
from notificaciones.models import Notificacion
from paquetes.models import Paquete

Usuario = get_user_model()


class AccionesDelPanelTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave', nombre='Admin', apellido='Atempo')
        self.maria = Usuario.objects.create_user('maria@correo.pe', 'Ritmo-propio-2026', nombre='María',
                                                 apellido='Salas', celular='987654321', dni='45678912')
        registrar_compra(self.maria, Paquete.objects.get(slug='atempo-10'), 'yape', '')
        base = HorarioBase.objects.first()
        inicio = timezone.now() + datetime.timedelta(hours=3)   # menos de 12 h: igual se devuelve si cancela el estudio
        clase = Clase.objects.create(inicio=inicio, sala=base.sala, disciplina=base.disciplina,
                                     instructor=base.instructor, nivel='suave')
        self.reserva = reservar(self.maria, clase)
        dia = timezone.localdate() + datetime.timedelta(days=2)
        while dia.weekday() != 1:
            dia += datetime.timedelta(days=1)
        tipo = TipoSesion.objects.get(nombre='Seguimiento')
        inicio, nutri = horas_libres('nutricion', tipo, dia, usuario=self.maria)[0]
        self.cita = agendar(self.maria, nutri, tipo, inicio)
        self.client.force_login(self.admin)

    def accion(self, url, accion, pk, confirmar=False):
        datos = {'action': accion, '_selected_action': [pk]}
        if confirmar:
            datos['post'] = 'yes'
        return self.client.post(url, datos, follow=True)

    def test_mismas_opciones_en_clases_y_en_nutricion_y_masajes(self):
        for url in ['/admin/clases/reserva/', '/admin/bienestar/cita/']:
            with self.subTest(url=url):
                pagina = self.client.get(url)
                self.assertContains(pagina, 'Cancelar las')
                self.assertContains(pagina, 'Eliminar sin devolver ni avisar (solo para pruebas)')
                self.assertContains(pagina, 'Cupos reservados')

    def test_seccion_clases_con_nombre_nuevo(self):
        self.assertContains(self.client.get('/admin/'), '>Clases<')

    def test_cancelar_reserva_devuelve_y_avisa(self):
        self.assertEqual(creditos_disponibles(self.maria), 9)
        respuesta = self.accion('/admin/clases/reserva/', 'cancelar_reservas_por_estudio', self.reserva.pk)
        self.assertContains(respuesta, '1 reserva cancelada')
        self.assertEqual(creditos_disponibles(self.maria), 10)
        self.assertTrue(self.maria.notificaciones.filter(texto__startswith='El estudio canceló tu reserva').exists())

    def test_cancelar_cita_devuelve_y_avisa(self):
        self.assertEqual(sesiones_incluidas_disponibles(self.maria, 'nutricion'), 0)
        respuesta = self.accion('/admin/bienestar/cita/', 'cancelar_por_estudio', self.cita.pk)
        self.assertContains(respuesta, '1 cita cancelada')
        self.assertEqual(sesiones_incluidas_disponibles(self.maria, 'nutricion'), 1)
        self.assertTrue(self.maria.notificaciones.filter(tipo=Notificacion.CITA_CANCELADA).exists())

    def test_reiniciar_cuenta_desde_la_ficha(self):
        ficha = self.client.get(f'/admin/cuentas/usuario/{self.maria.pk}/change/')
        self.assertContains(ficha, 'Reiniciar cuenta de prueba')
        # Primero muestra la confirmación, sin borrar nada
        confirmacion = self.client.get('/admin/cuentas/usuario/reiniciar/', {'ids': self.maria.pk})
        self.assertContains(confirmacion, 'No se puede deshacer')
        self.assertContains(confirmacion, 'maria@correo.pe')
        self.assertTrue(self.maria.compras.exists())
        # Al confirmar, la cuenta queda como recién creada
        respuesta = self.client.post('/admin/cuentas/usuario/reiniciar/',
                                     {'ids': str(self.maria.pk), 'confirmar': '1'}, follow=True)
        self.assertContains(respuesta, 'Cuenta reiniciada: María Salas')
        for relacion in ['compras', 'reservas', 'citas', 'notificaciones']:
            self.assertFalse(getattr(self.maria, relacion).exists(), relacion)
        self.maria.refresh_from_db()
        self.assertEqual(self.maria.dni, '45678912')           # los datos personales se mantienen
        self.assertTrue(self.maria.codigo_referida)

    def test_reiniciar_varias_desde_la_lista(self):
        ana = Usuario.objects.create_user('ana@correo.pe', 'Ritmo-propio-2026', nombre='Ana', apellido='Paz',
                                          celular='912345678', dni='12345678')
        registrar_compra(ana, Paquete.objects.get(slug='atempo-5'), 'yape', '')
        respuesta = self.client.post('/admin/cuentas/usuario/', {
            'action': 'reiniciar_cuentas', '_selected_action': [self.maria.pk, ana.pk]}, follow=True)
        self.assertContains(respuesta, 'Reiniciar cuenta de prueba')
        self.client.post('/admin/cuentas/usuario/reiniciar/', {'ids': f'{self.maria.pk},{ana.pk}', 'confirmar': '1'})
        self.assertFalse(ana.compras.exists())
        self.assertFalse(self.maria.compras.exists())

    def test_eliminar_borra_sin_devolver(self):
        self.accion('/admin/clases/reserva/', 'delete_selected', self.reserva.pk, confirmar=True)
        self.accion('/admin/bienestar/cita/', 'delete_selected', self.cita.pk, confirmar=True)
        self.assertFalse(Reserva.objects.exists())
        self.assertFalse(Cita.objects.exists())
        self.assertEqual(creditos_disponibles(self.maria), 9)                      # no se devolvió
        self.assertEqual(sesiones_incluidas_disponibles(self.maria, 'nutricion'), 0)
