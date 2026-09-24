import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from compras.models import Compra, creditos_disponibles, registrar_compra
from notificaciones.models import Notificacion
from paquetes.models import Paquete

from .models import AFORO, Clase, HorarioBase, Profesional, Reserva
from .servicios import (NoSePuedeReservar, cancelar_clase_por_estudio, cancelar_reserva, generar_clases,
                        reservar)

Usuario = get_user_model()


def cuenta(nombre='María', n=1):
    return Usuario.objects.create_user(f'{nombre.lower()}{n}@correo.pe', 'Ritmo-propio-2026', nombre=nombre,
                                       apellido='Salas', celular=f'9{n:08d}', dni=f'{n:08d}')


def clase_en(horas, sala_orden=0):
    """Una clase que empieza dentro de `horas` horas."""
    base = HorarioBase.objects.filter(sala__orden=sala_orden).first()
    inicio = (timezone.now() + datetime.timedelta(hours=horas)).replace(second=0, microsecond=0)
    return Clase.objects.create(inicio=inicio, sala=base.sala, disciplina=base.disciplina,
                                instructor=base.instructor, nivel='suave', ocupacion_simulada=5)


def comprar(usuario, slug='atempo-5'):
    return registrar_compra(usuario, Paquete.objects.get(slug=slug), 'yape', '')


class DatosInicialesTests(TestCase):
    def test_semana_tipo_de_156_clases_y_equipo_del_excel(self):
        self.assertEqual(HorarioBase.objects.count(), 156)
        self.assertEqual(Profesional.objects.filter(area='instruccion').count(), 7)
        self.assertEqual(Profesional.objects.filter(area='nutricion').count(), 2)
        self.assertEqual(Profesional.objects.filter(area='masajes').count(), 1)

    def test_nadie_tiene_dos_clases_a_la_misma_hora(self):
        for dia in range(7):
            for hora in HorarioBase.objects.filter(dia_semana=dia).values_list('hora', flat=True).distinct():
                instructores = list(HorarioBase.objects.filter(dia_semana=dia, hora=hora)
                                    .values_list('instructor', flat=True))
                self.assertEqual(len(instructores), len(set(instructores)), f'día {dia} {hora}')

    def test_generar_clases_de_los_proximos_dias(self):
        creadas = generar_clases()
        self.assertGreaterEqual(creadas, 156)
        self.assertEqual(generar_clases(), 0)   # no duplica


class ReservarTests(TestCase):
    def setUp(self):
        self.maria = cuenta()

    def test_reservar_usa_un_credito(self):
        comprar(self.maria)
        reserva = reservar(self.maria, clase_en(48))
        self.assertEqual(creditos_disponibles(self.maria), 4)
        self.assertEqual(reserva.compra.nombre_paquete, 'Atempo 5')

    def test_sin_creditos(self):
        with self.assertRaisesMessage(NoSePuedeReservar, 'SIN_CREDITOS'):
            reservar(self.maria, clase_en(48))

    def test_el_credito_debe_estar_vigente_el_dia_de_la_clase(self):
        compra = comprar(self.maria)
        Compra.objects.filter(pk=compra.pk).update(vence=timezone.localdate() + datetime.timedelta(days=1))
        with self.assertRaisesMessage(NoSePuedeReservar, 'SIN_CREDITOS'):
            reservar(self.maria, clase_en(24 * 4))

    def test_usa_el_que_vence_antes_entre_los_vigentes_ese_dia(self):
        cinco = comprar(self.maria, 'atempo-5')
        diez = comprar(self.maria, 'atempo-10')
        reserva = reservar(self.maria, clase_en(48))
        self.assertEqual(reserva.compra, cinco)
        Compra.objects.filter(pk=cinco.pk).update(vence=timezone.localdate() + datetime.timedelta(days=2))
        reserva = reservar(self.maria, clase_en(24 * 5, sala_orden=1))
        self.assertEqual(reserva.compra, diez)

    def test_no_dos_veces_ni_dos_a_la_misma_hora(self):
        comprar(self.maria)
        clase = clase_en(48)
        reservar(self.maria, clase)
        with self.assertRaisesMessage(NoSePuedeReservar, 'Ya tienes una reserva en esta clase.'):
            reservar(self.maria, clase)
        otra = Clase.objects.create(inicio=clase.inicio, sala=HorarioBase.objects.filter(sala__orden=1).first().sala,
                                    disciplina=clase.disciplina, instructor=clase.instructor, nivel='media')
        with self.assertRaisesMessage(NoSePuedeReservar, 'otra clase reservada a esa misma hora'):
            reservar(self.maria, otra)

    def test_maximo_7_dias_de_anticipacion(self):
        comprar(self.maria, 'atempo-10')
        with self.assertRaisesMessage(NoSePuedeReservar, 'hasta 7 días'):
            reservar(self.maria, clase_en(24 * 9))

    def test_clase_llena_solo_con_simulacion(self):
        comprar(self.maria)
        clase = clase_en(48)
        Clase.objects.filter(pk=clase.pk).update(ocupacion_simulada=AFORO)
        clase.refresh_from_db()
        with self.assertRaisesMessage(NoSePuedeReservar, 'llena'):
            reservar(self.maria, clase, simular=True)
        reservar(self.maria, clase, simular=False)   # sin simulación, solo cuentan las reales


class CancelarTests(TestCase):
    def setUp(self):
        self.maria = cuenta()
        comprar(self.maria)

    def test_con_12_horas_o_mas_se_devuelve(self):
        reserva = reservar(self.maria, clase_en(13))
        self.assertTrue(cancelar_reserva(reserva))
        self.assertEqual(creditos_disponibles(self.maria), 5)

    def test_con_menos_de_12_horas_no_se_devuelve(self):
        reserva = reservar(self.maria, clase_en(5))
        self.assertFalse(cancelar_reserva(reserva))
        self.assertEqual(creditos_disponibles(self.maria), 4)
        self.assertTrue(Reserva.objects.get(pk=reserva.pk).cancelada)   # igual libera el cupo

    def test_el_estudio_cancela_una_clase(self):
        clase = clase_en(3)
        reservar(self.maria, clase)
        self.assertEqual(cancelar_clase_por_estudio(clase), 1)
        self.assertEqual(creditos_disponibles(self.maria), 5)          # siempre se devuelve
        aviso = self.maria.notificaciones.get(tipo=Notificacion.CLASE_CANCELADA)
        self.assertIn('Te devolvimos tu punto', aviso.texto)


class PaginasTests(TestCase):
    def setUp(self):
        self.maria = cuenta()
        generar_clases()

    def test_horario_publico(self):
        respuesta = self.client.get(reverse('horarios'))
        for texto in ['<h1>Clases</h1>', 'id="zona-horario" data-zona', 'Hoy', 'Mañana', 'Pilates', 'Sala Calma', 'Todo el día',
                      'Temprano (antes de 9:00)', 'Simular ocupación']:
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, '12 cupos')   # el aforo no se muestra

    def test_filtros(self):
        manana = timezone.localdate() + datetime.timedelta(days=1)
        respuesta = self.client.get(reverse('horarios'), {'dia': manana.isoformat(), 'disciplina': 'zumba'})
        self.assertContains(respuesta, 'Sala Ritmo')
        self.assertNotContains(respuesta, '<h3>Pilates</h3>')

    def test_reservar_sin_sesion_pide_ingresar(self):
        clase = clase_en(48)
        respuesta = self.client.get(reverse('reservar', args=[clase.pk]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('ingresar'), respuesta.url)

    def test_confirmacion_y_reserva(self):
        comprar(self.maria)
        clase = clase_en(48)
        self.client.force_login(self.maria)
        confirmacion = self.client.get(reverse('reservar', args=[clase.pk]), {'parcial': 1})
        self.assertContains(confirmacion, 'Confirma tu reserva')
        self.assertContains(confirmacion, 'Se usará 1 punto de')
        self.assertNotContains(confirmacion, '<html')                  # es solo el contenido de la ventana
        respuesta = self.client.post(reverse('reservar', args=[clase.pk]), follow=True)
        self.assertContains(respuesta, '¡Listo! Reservaste')
        self.assertTrue(clase.reservas.filter(usuario=self.maria).exists())

    def test_advierte_antes_de_confirmar_si_faltan_menos_de_12_horas(self):
        comprar(self.maria)
        self.client.force_login(self.maria)
        pronto = self.client.get(reverse('reservar', args=[clase_en(5).pk]), {'parcial': 1})
        self.assertContains(pronto, 'esta clase empieza en menos de 12 horas')
        self.assertContains(pronto, 'no recuperarás el punto')
        lejos = self.client.get(reverse('reservar', args=[clase_en(48, sala_orden=1).pk]), {'parcial': 1})
        self.assertNotContains(lejos, 'no recuperarás el punto')
        self.assertContains(lejos, 'Puedes cancelar sin perder el punto')

    def test_al_reservar_llega_notificacion(self):
        comprar(self.maria)
        self.client.force_login(self.maria)
        self.client.post(reverse('reservar', args=[clase_en(48).pk]))
        aviso = self.maria.notificaciones.get(tipo=Notificacion.RESERVA_CONFIRMADA)
        self.assertTrue(aviso.texto.startswith('Reserva confirmada:'))

    def test_dias_con_dos_digitos(self):
        respuesta = self.client.get(reverse('horarios'))
        dia = timezone.localdate() + datetime.timedelta(days=3)
        self.assertContains(respuesta, f'<span class="dia-numero cifra">{dia:%d}</span>')

    def test_sin_creditos_ofrece_paquetes(self):
        self.client.force_login(self.maria)
        Compra.objects.all().delete()
        respuesta = self.client.get(reverse('reservar', args=[clase_en(48).pk]), {'parcial': 1})
        self.assertContains(respuesta, 'Necesitas un punto vigente')
        self.assertContains(respuesta, 'Ver paquetes')

    def test_simulacion_apagada_por_defecto_y_se_puede_prender(self):
        self.assertFalse(self.client.session.get('simular_ocupacion', False))
        self.client.post(reverse('simular_ocupacion'))
        self.assertTrue(self.client.session['simular_ocupacion'])
        self.assertContains(self.client.get(reverse('horarios')), 'Dejar de simular')

    def test_mi_cuenta_agrupa_las_clases_por_dia(self):
        comprar(self.maria, 'atempo-10')
        reservar(self.maria, clase_en(48))
        reservar(self.maria, clase_en(49, sala_orden=1))
        reservar(self.maria, clase_en(72, sala_orden=2))
        self.client.force_login(self.maria)
        html = self.client.get(reverse('cuenta')).content.decode()
        self.assertEqual(html.count('class="dia-agrupado"'), 2)   # dos días, tres clases

    def test_textos_en_puntos(self):
        self.assertNotContains(self.client.get(reverse('paquetes')), 'crédito')
        self.assertContains(self.client.get(reverse('paquetes')), 'puntos')

    def test_mi_cuenta_muestra_proximas_clases_y_cancelar(self):
        comprar(self.maria)
        reserva = reservar(self.maria, clase_en(48))
        self.client.force_login(self.maria)
        respuesta = self.client.get(reverse('cuenta'))
        self.assertContains(respuesta, 'Próximas clases')
        self.assertContains(respuesta, reverse('cancelar_reserva', args=[reserva.pk]))
        cancelar = self.client.post(reverse('cancelar_reserva', args=[reserva.pk]), follow=True)
        self.assertContains(cancelar, 'Tu punto ya está de vuelta')

    def test_recordatorio_24_horas_antes_una_sola_vez(self):
        comprar(self.maria)
        reservar(self.maria, clase_en(20))
        self.client.force_login(self.maria)
        self.client.get(reverse('inicio'))
        self.client.get(reverse('horarios'))
        avisos = self.maria.notificaciones.filter(tipo=Notificacion.RECORDATORIO)
        self.assertEqual(avisos.count(), 1)
        self.assertIn('tienes', avisos.get().texto)

    def test_inicio_y_nosotros_usan_los_datos_del_panel(self):
        inicio = self.client.get(reverse('inicio'))
        self.assertContains(inicio, 'Pilates')
        nosotros = self.client.get(reverse('nosotros'))
        for nombre in ['Karol G', 'Wisin', 'Becky G', 'J Balvin', 'Lic. María Becerra', 'Lic. Nicki Nicole',
                       'De La Rose']:
            self.assertContains(nosotros, nombre)
