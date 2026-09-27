import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from compras.models import registrar_compra
from notificaciones.models import Notificacion
from paquetes.models import Paquete

from . import asistencia
from .models import Clase, Disciplina, Profesional, Reserva, Sala

Usuario = get_user_model()
ZONA = timezone.get_current_timezone()


def socia(n=1):
    usuaria = Usuario.objects.create_user(f'socia{n}@correo.pe', 'Ritmo-propio-2026', nombre=f'Socia{n}',
                                          apellido='Prueba', celular=f'9{n:08d}', dni=f'{n:08d}')
    registrar_compra(usuaria, Paquete.objects.get(slug='atempo-10'), 'yape', '')
    return usuaria


def clase_en(inicio):
    return Clase.objects.create(inicio=inicio, sala=Sala.objects.first(), disciplina=Disciplina.objects.first(),
                                instructor=Profesional.objects.filter(area='instruccion').first(), nivel='media')


def reserva(usuaria, clase):
    return Reserva.objects.create(usuario=usuaria, clase=clase, compra=usuaria.compras.first())


class AsistenciaTests(TestCase):
    def setUp(self):
        self.ana = socia(1)
        self.ahora = timezone.now()

    def test_marcar_y_desmarcar_el_mismo_dia(self):
        clase = clase_en(self.ahora + datetime.timedelta(minutes=30))
        if clase.fecha != timezone.localdate():
            self.skipTest('Muy cerca de la medianoche')
        r = reserva(self.ana, clase)
        asistencia.marcar(r, True)
        self.assertEqual(r.asistencia, Reserva.ASISTIO)
        asistencia.marcar(r, False)
        self.assertEqual(r.asistencia, Reserva.POR_REGISTRAR)

    def test_no_se_marca_otro_dia(self):
        r = reserva(self.ana, clase_en(self.ahora + datetime.timedelta(days=2)))
        with self.assertRaises(asistencia.NoSePuedeMarcar):
            asistencia.marcar(r, True)

    def test_al_terminar_la_clase_queda_no_asistio(self):
        terminada = reserva(self.ana, clase_en(self.ahora - datetime.timedelta(hours=2)))
        futura = reserva(self.ana, clase_en(self.ahora + datetime.timedelta(hours=2)))
        asistencia.revisar_asistencia()
        terminada.refresh_from_db()
        futura.refresh_from_db()
        self.assertEqual(terminada.asistencia, Reserva.NO_ASISTIO)
        self.assertEqual(futura.asistencia, Reserva.POR_REGISTRAR)

    def test_aviso_amable_tras_3_inasistencias_en_el_mes(self):
        # Mediados de mes, para que las 3 clases caigan en el mismo mes
        mitad = timezone.make_aware(datetime.datetime(2026, 10, 15, 12, 0), ZONA)
        for horas in (30, 20, 10):
            reserva(self.ana, clase_en(mitad - datetime.timedelta(hours=horas)))
        with mock.patch('django.utils.timezone.now', return_value=mitad):
            asistencia.revisar_asistencia()
            asistencia.revisar_asistencia()
        avisos = self.ana.notificaciones.filter(tipo=Notificacion.INASISTENCIAS)
        self.assertEqual(avisos.count(), 1)   # una sola vez por mes
        self.assertIn('cancela antes', avisos.get().texto)

    def test_con_2_inasistencias_no_hay_aviso(self):
        for horas in (20, 10):
            reserva(self.ana, clase_en(self.ahora - datetime.timedelta(hours=horas)))
        asistencia.revisar_asistencia()
        self.assertFalse(self.ana.notificaciones.filter(tipo=Notificacion.INASISTENCIAS).exists())

    def test_resumen(self):
        bea = socia(2)
        clase = clase_en(self.ahora - datetime.timedelta(hours=3))
        r1, r2 = reserva(self.ana, clase), reserva(bea, clase)
        Reserva.objects.filter(pk=r1.pk).update(asistencia=Reserva.ASISTIO)
        asistencia.revisar_asistencia()
        datos = asistencia.resumen(7)
        total = datos['total']
        self.assertEqual((total['clases'], total['reservas'], total['asistencias']), (1, 2, 1))
        self.assertEqual(total['asistencia'], 50)
        self.assertEqual(total['ocupacion'], round(100 / clase.aforo))
        self.assertEqual(datos['mas_faltas'][0], (bea, 1))


class PanelRecepcionTests(TestCase):
    def setUp(self):
        self.ana = socia(1)
        admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave', nombre='Admin', apellido='Atempo')
        self.client.force_login(admin)

    def test_seccion_recepcion_en_el_panel_y_la_barra_lateral(self):
        inicio = self.client.get('/admin/')
        self.assertContains(inicio, 'Recepción')
        self.assertContains(inicio, 'href="/admin/recepcion/asistencia/"')
        # En la barra lateral de las páginas propias, marcada la actual (y no "Cupos reservados")
        resumen = self.client.get(reverse('admin:clases_resumen'))
        self.assertContains(resumen, 'href="/admin/recepcion/resumen/" aria-current="page"')
        self.assertNotContains(resumen, 'href="/admin/clases/reserva/" aria-current="page"')
        self.assertRedirects(self.client.get('/admin/recepcion/'), reverse('admin:clases_asistencia'))

    def test_buscar_por_dni_y_marcar(self):
        inicio = timezone.now() + datetime.timedelta(minutes=30)
        if timezone.localtime(inicio).date() != timezone.localdate():
            self.skipTest('Muy cerca de la medianoche')
        r = reserva(self.ana, clase_en(inicio))
        pagina = self.client.get(reverse('admin:clases_asistencia') + '?q=00000001')
        self.assertContains(pagina, 'Socia1 Prueba')
        self.assertContains(pagina, 'Marcar asistió')
        self.client.post(reverse('admin:clases_asistencia_marcar', args=[r.pk]), {'asistio': '1'})
        r.refresh_from_db()
        self.assertEqual(r.asistencia, Reserva.ASISTIO)
        self.assertContains(self.client.get(reverse('admin:clases_asistencia')), '1 de 1 asistieron')

    def test_dni_sin_reservas_hoy(self):
        pagina = self.client.get(reverse('admin:clases_asistencia') + '?q=99999999')
        self.assertContains(pagina, 'No hay reservas para hoy')

    def test_resumen_carga(self):
        self.assertEqual(self.client.get(reverse('admin:clases_resumen') + '?dias=90').status_code, 200)


class CorreoDeConfirmacionTests(TestCase):
    def test_en_mi_cuenta_y_sin_dni(self):
        ana = socia(1)
        reserva(ana, clase_en(timezone.now() + datetime.timedelta(days=1)))
        self.client.force_login(ana)
        respuesta = self.client.get(reverse('cuenta'))
        self.assertContains(respuesta, 'Ver el correo de confirmación')
        self.assertContains(respuesta, 'presenta tu DNI en recepción')
        cuerpo = respuesta.content.decode().split('Ver el correo de confirmación')[1]
        self.assertNotIn('00000001', cuerpo.split('</details>')[0])   # el correo no lleva el DNI
