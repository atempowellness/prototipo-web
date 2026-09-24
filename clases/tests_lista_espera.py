import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from compras.models import registrar_compra
from notificaciones.models import Notificacion
from paquetes.models import Paquete

from .lista_espera import (MAXIMO_LISTAS, NoSePuedeAnotar, anotarse, confirmar, fin_del_plazo, inicio_del_plazo,
                           motivo_para_no_anotarse, procesar_lista, salir, simular_cupo_liberado)
from .models import Clase, Disciplina, ListaEspera, Profesional, Reserva, Sala
from .servicios import cancelar_reserva, reservar

Usuario = get_user_model()
ZONA = timezone.get_current_timezone()


def momento(dia, hora, minuto=0):
    return timezone.make_aware(datetime.datetime.combine(dia, datetime.time(hora, minuto)), ZONA)


def socia(n):
    usuaria = Usuario.objects.create_user(f'socia{n}@correo.pe', 'Ritmo-propio-2026', nombre=f'Socia{n}',
                                          apellido='Prueba', celular=f'9{n:08d}', dni=f'{n:08d}')
    registrar_compra(usuaria, Paquete.objects.get(slug='atempo-10'), 'yape', '')
    return usuaria


def crear_clase(inicio, aforo=1):
    return Clase.objects.create(inicio=inicio, sala=Sala.objects.first(), disciplina=Disciplina.objects.first(),
                                instructor=Profesional.objects.filter(area='instruccion').first(), nivel='media',
                                aforo=aforo)


class PlazosTests(TestCase):
    """Los 45 minutos no corren de 22:00 a 5:00 y nunca pasan del cierre (2 horas antes)."""

    def setUp(self):
        self.manana = timezone.localdate() + datetime.timedelta(days=2)
        self.clase = crear_clase(momento(self.manana, 18, 0))

    def test_de_dia_son_45_minutos(self):
        self.assertEqual(fin_del_plazo(momento(self.manana, 10, 0), self.clase), momento(self.manana, 10, 45))

    def test_de_noche_empieza_a_las_5(self):
        noche = momento(self.manana - datetime.timedelta(days=1), 23, 30)
        self.assertEqual(inicio_del_plazo(noche), momento(self.manana, 5, 0))
        self.assertEqual(fin_del_plazo(noche, self.clase), momento(self.manana, 5, 45))

    def test_se_pausa_a_las_22(self):
        dia = self.manana - datetime.timedelta(days=1)
        self.assertEqual(fin_del_plazo(momento(dia, 21, 40), self.clase), momento(self.manana, 5, 25))

    def test_no_pasa_del_cierre(self):
        self.assertEqual(fin_del_plazo(momento(self.manana, 15, 30), self.clase), momento(self.manana, 16, 0))


class ListaEsperaTests(TestCase):
    def setUp(self):
        self.ana, self.bea, self.caro = socia(1), socia(2), socia(3)
        dia = timezone.localdate() + datetime.timedelta(days=2)
        self.clase = crear_clase(momento(dia, 18, 0), aforo=1)
        self.reserva_ana = reservar(self.ana, self.clase)

    def test_anotarse_y_puesto(self):
        bea = anotarse(self.bea, self.clase)
        caro = anotarse(self.caro, self.clase)
        self.assertEqual((bea.puesto, caro.puesto), (1, 2))
        self.assertEqual(motivo_para_no_anotarse(self.bea, self.clase), 'Ya estás en la lista de espera de esta clase.')
        self.assertEqual(motivo_para_no_anotarse(self.ana, self.clase), 'Ya tienes una reserva en esta clase.')

    def test_requisitos(self):
        sin_puntos = Usuario.objects.create_user('sin@correo.pe', 'x', nombre='Sin', apellido='Puntos',
                                                 celular='911111111', dni='11111111')
        self.assertEqual(motivo_para_no_anotarse(sin_puntos, self.clase), 'SIN_CREDITOS')
        # Con cupo libre no hay lista
        libre = crear_clase(self.clase.inicio + datetime.timedelta(hours=1), aforo=5)
        self.assertIn('todavía tiene cupos', motivo_para_no_anotarse(self.bea, libre))
        # Hasta 3 listas a la vez
        for n in range(MAXIMO_LISTAS):
            otra = crear_clase(self.clase.inicio + datetime.timedelta(days=1, hours=n), aforo=1)
            reservar(self.ana, otra)
            anotarse(self.bea, otra)
        self.assertIn('hasta 3 listas', motivo_para_no_anotarse(self.bea, self.clase))

    def test_cupo_liberado_se_ofrece_y_se_confirma(self):
        bea = anotarse(self.bea, self.clase)
        anotarse(self.caro, self.clase)
        cancelar_reserva(self.reserva_ana)
        bea.refresh_from_db()
        self.assertEqual(bea.estado, ListaEspera.OFRECIDO)
        self.assertIsNotNone(bea.oferta_vence)
        self.assertEqual(self.clase.cupos(), 0)        # el cupo está guardado para ella
        self.assertTrue(self.bea.notificaciones.filter(tipo=Notificacion.ESPERA_OFERTA).exists())

        usados = self.bea.compras.get().creditos_usados
        reserva = confirmar(bea)
        self.assertEqual(reserva.usuario, self.bea)
        self.assertEqual(self.bea.compras.get().creditos_usados, usados + 1)   # el punto se cobra al confirmar
        bea.refresh_from_db()
        self.assertEqual(bea.estado, ListaEspera.CONFIRMADO)

    def test_si_no_confirma_pasa_a_la_siguiente(self):
        bea = anotarse(self.bea, self.clase)
        caro = anotarse(self.caro, self.clase)
        cancelar_reserva(self.reserva_ana)
        ListaEspera.objects.filter(pk=bea.pk).update(oferta_vence=timezone.now() - datetime.timedelta(minutes=1))
        procesar_lista(self.clase)
        bea.refresh_from_db()
        caro.refresh_from_db()
        self.assertEqual(bea.estado, ListaEspera.VENCIDO)
        self.assertEqual(caro.estado, ListaEspera.OFRECIDO)
        self.assertTrue(self.bea.notificaciones.filter(tipo=Notificacion.ESPERA_VENCIDA).exists())
        with self.assertRaises(NoSePuedeAnotar):
            confirmar(bea)

    def test_dejarlo_pasar(self):
        bea = anotarse(self.bea, self.clase)
        caro = anotarse(self.caro, self.clase)
        cancelar_reserva(self.reserva_ana)
        salir(ListaEspera.objects.get(pk=bea.pk))
        caro.refresh_from_db()
        self.assertEqual(caro.estado, ListaEspera.OFRECIDO)

    def test_se_salta_a_quien_no_tiene_punto(self):
        bea = anotarse(self.bea, self.clase)
        caro = anotarse(self.caro, self.clase)
        self.bea.compras.update(creditos_usados=10)
        cancelar_reserva(self.reserva_ana)
        bea.refresh_from_db()
        caro.refresh_from_db()
        self.assertEqual(bea.estado, ListaEspera.OMITIDO)
        self.assertEqual(caro.estado, ListaEspera.OFRECIDO)

    def test_de_noche_si_ya_no_alcanza_queda_libre(self):
        """Clase de 6:30: la lista cierra a las 4:30. Si el cupo se libera a las 23:00, queda libre."""
        dia = timezone.localdate() + datetime.timedelta(days=2)
        temprano = crear_clase(momento(dia, 6, 30), aforo=1)
        reserva = reservar(self.ana, temprano)
        bea = anotarse(self.bea, temprano)
        with mock.patch('django.utils.timezone.now', return_value=momento(dia - datetime.timedelta(days=1), 23, 0)):
            cancelar_reserva(reserva)
        bea.refresh_from_db()
        self.assertEqual(bea.estado, ListaEspera.CERRADO)
        self.assertEqual(temprano.cupos(), 1)
        self.assertIn('puedes reservarlo directamente', self.bea.notificaciones.get(tipo=Notificacion.ESPERA_FIN).texto)

    def test_la_lista_cierra_2_horas_antes(self):
        bea = anotarse(self.bea, self.clase)
        with mock.patch('django.utils.timezone.now', return_value=self.clase.inicio - datetime.timedelta(hours=1)):
            procesar_lista(self.clase)
        bea.refresh_from_db()
        self.assertEqual(bea.estado, ListaEspera.CERRADO)
        self.assertIn('no se liberó ningún cupo', self.bea.notificaciones.get(tipo=Notificacion.ESPERA_FIN).texto)


class PaginasListaEsperaTests(TestCase):
    def setUp(self):
        self.ana, self.bea = socia(1), socia(2)
        from clases.views import asegurar_clases
        asegurar_clases()
        self.clase = (Clase.objects.filter(inicio__gt=timezone.now() + datetime.timedelta(hours=6))
                      .order_by('inicio').first())
        Clase.objects.filter(pk=self.clase.pk).update(aforo=1)
        self.clase.refresh_from_db()
        self.reserva = reservar(self.ana, self.clase)
        self.url_dia = reverse('horarios') + f'?dia={self.clase.fecha.isoformat()}'

    def test_flujo_completo_en_la_web(self):
        self.client.force_login(self.bea)
        self.assertContains(self.client.get(self.url_dia), 'Lista de espera</a>')
        ventana = self.client.get(reverse('anotarse_espera', args=[self.clase.pk]) + '?parcial=1')
        self.assertContains(ventana, 'Serías la primera en la lista')
        respuesta = self.client.post(reverse('anotarse_espera', args=[self.clase.pk]), follow=True)
        self.assertContains(respuesta, 'Eres la 1.ª en la lista')
        self.assertContains(respuesta, 'En lista de espera: eres la 1.ª')
        self.assertContains(self.client.get(reverse('cuenta')), 'Listas de espera')

        # Ana cancela: a Bea le llega la oferta, con el correo simulado arriba
        cancelar_reserva(self.reserva)
        pagina = self.client.get(self.url_dia)
        self.assertContains(pagina, '¡Se liberó un cupo para ti!')
        self.assertContains(pagina, 'Ver el correo que te enviamos')
        puesto = ListaEspera.objects.get(usuario=self.bea)
        respuesta = self.client.post(reverse('confirmar_cupo', args=[puesto.pk]), follow=True)
        self.assertContains(respuesta, '¡Listo! Tienes tu cupo')
        self.assertTrue(Reserva.objects.filter(usuario=self.bea, clase=self.clase, cancelada=False).exists())

    def test_demostracion_simular_cupo(self):
        Clase.objects.filter(pk=self.clase.pk).update(aforo=6, ocupacion_simulada=5)
        self.client.force_login(self.bea)
        self.client.post(reverse('simular_ocupacion'))           # modo demostración
        self.client.post(reverse('anotarse_espera', args=[self.clase.pk]))
        self.clase.refresh_from_db()
        self.assertTrue(self.clase.ocupacion_fija)
        self.assertContains(self.client.get(self.url_dia), 'Simular que se libera un cupo')
        self.assertTrue(simular_cupo_liberado(self.clase))
        self.assertEqual(ListaEspera.objects.get(usuario=self.bea).estado, ListaEspera.OFRECIDO)

    def test_panel_adelantar_el_reloj(self):
        anotarse(self.bea, self.clase)
        cancelar_reserva(self.reserva)
        admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave', nombre='Admin', apellido='Atempo')
        self.client.force_login(admin)
        puesto = ListaEspera.objects.get(usuario=self.bea)
        self.client.post('/admin/clases/listaespera/', {'action': 'vencer_ofertas', '_selected_action': [puesto.pk]})
        puesto.refresh_from_db()
        self.assertEqual(puesto.estado, ListaEspera.VENCIDO)

    def test_reiniciar_cuenta_libera_su_puesto(self):
        from cuentas.admin import reiniciar_cuenta
        anotarse(self.bea, self.clase)
        reiniciar_cuenta(self.bea)
        self.assertFalse(ListaEspera.objects.exists())
