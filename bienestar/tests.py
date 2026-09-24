import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clases.models import Profesional
from compras.models import Compra, creditos_disponibles, registrar_compra
from notificaciones.models import Notificacion
from paquetes.models import Paquete

from .models import MASAJES, NUTRICION, Cita, TipoSesion
from .servicios import (NoSePuedeAgendar, agendar, cancelar_cita, horas_libres, plan_de_pago,
                        sesiones_incluidas_disponibles)

Usuario = get_user_model()


def cuenta(nombre='María', n=1):
    return Usuario.objects.create_user(f'{nombre.lower()}{n}@correo.pe', 'Ritmo-propio-2026', nombre=nombre,
                                       apellido='Salas', celular=f'9{n:08d}', dni=f'{n:08d}')


def comprar(usuario, slug):
    return registrar_compra(usuario, Paquete.objects.get(slug=slug), 'yape', '')


def proximo(dia_semana):
    """El próximo día de la semana indicado (0 = lunes), al menos 2 días desde hoy."""
    dia = timezone.localdate() + datetime.timedelta(days=2)
    while dia.weekday() != dia_semana:
        dia += datetime.timedelta(days=1)
    return dia


def primera_hora(servicio, tipo, dia, usuario=None):
    return horas_libres(servicio, tipo, dia, usuario=usuario)[0]


class DatosInicialesTests(TestCase):
    def test_tipos_y_horarios(self):
        self.assertEqual(TipoSesion.objects.filter(servicio=NUTRICION).count(), 2)
        self.assertEqual(TipoSesion.objects.filter(servicio=MASAJES).count(), 2)
        martes = proximo(1)
        evaluacion = TipoSesion.objects.get(nombre__startswith='Evaluación')
        quienes = {p.nombre for _, p in horas_libres(NUTRICION, evaluacion, martes)}
        self.assertEqual(quienes, {'Lic. María Becerra', 'Lic. Nicki Nicole'})


class PlanDePagoTests(TestCase):
    def setUp(self):
        self.maria = cuenta()
        self.dia = proximo(1)
        self.evaluacion = TipoSesion.objects.get(nombre__startswith='Evaluación')
        self.descarga = TipoSesion.objects.get(nombre='Descarga muscular')

    def test_sin_paquete_no_esta_habilitado(self):
        plan = plan_de_pago(self.maria, NUTRICION, self.dia)
        self.assertEqual(plan.modo, 'no_habilitado')
        self.assertEqual(plan.paquete_minimo, 'Atempo 10')

    def test_primero_usa_la_incluida(self):
        comprar(self.maria, 'atempo-5')
        inicio, nutri = primera_hora(NUTRICION, self.evaluacion, self.dia, self.maria)
        cita = agendar(self.maria, nutri, self.evaluacion, inicio)
        self.assertEqual(cita.forma, Cita.INCLUIDA)
        self.assertEqual(sesiones_incluidas_disponibles(self.maria, NUTRICION), 0)
        self.assertEqual(creditos_disponibles(self.maria), 5)   # no toca los créditos

    def test_atempo_5_no_permite_nutricion_adicional(self):
        comprar(self.maria, 'atempo-5')
        inicio, nutri = primera_hora(NUTRICION, self.evaluacion, self.dia, self.maria)
        agendar(self.maria, nutri, self.evaluacion, inicio)
        self.assertEqual(plan_de_pago(self.maria, NUTRICION, self.dia).modo, 'no_habilitado')

    def test_adicional_con_creditos_desde_atempo_10(self):
        comprar(self.maria, 'atempo-10')
        for _ in range(2):   # la 1.ª incluida, la 2.ª adicional (1 crédito)
            inicio, nutri = primera_hora(NUTRICION, self.evaluacion, self.dia, self.maria)
            cita = agendar(self.maria, nutri, self.evaluacion, inicio)
        self.assertEqual(cita.forma, Cita.CREDITOS)
        self.assertEqual(creditos_disponibles(self.maria), 9)

    def test_masaje_adicional_cuesta_2_creditos_desde_atempo_20(self):
        comprar(self.maria, 'atempo-10')
        self.assertEqual(plan_de_pago(self.maria, MASAJES, self.dia).modo, 'no_habilitado')
        comprar(self.maria, 'atempo-20')
        inicio, masajista = primera_hora(MASAJES, self.descarga, self.dia, self.maria)
        self.assertEqual(agendar(self.maria, masajista, self.descarga, inicio).forma, Cita.INCLUIDA)
        inicio, masajista = primera_hora(MASAJES, self.descarga, self.dia, self.maria)
        cita = agendar(self.maria, masajista, self.descarga, inicio)
        self.assertEqual(cita.forma, Cita.CREDITOS)
        self.assertEqual(len(cita.compras_creditos), 2)
        self.assertEqual(creditos_disponibles(self.maria), 28)


class HorasLibresTests(TestCase):
    def setUp(self):
        self.maria = cuenta()
        comprar(self.maria, 'atempo-20')
        self.dia = proximo(1)
        self.seguimiento = TipoSesion.objects.get(nombre='Seguimiento')

    def test_una_hora_tomada_ya_no_aparece(self):
        inicio, nutri = primera_hora(NUTRICION, self.seguimiento, self.dia)
        agendar(self.maria, nutri, self.seguimiento, inicio)
        self.assertNotIn((inicio, nutri), horas_libres(NUTRICION, self.seguimiento, self.dia, nutri))
        with self.assertRaisesMessage(NoSePuedeAgendar, 'ya no está disponible'):
            agendar(cuenta('Ana', 2), nutri, self.seguimiento, inicio)

    def test_elegir_profesional(self):
        nicki = Profesional.objects.get(nombre='Lic. Nicki Nicole')
        self.assertTrue(all(p == nicki for _, p in horas_libres(NUTRICION, self.seguimiento, self.dia, nicki)))

    def test_no_choca_con_sus_clases(self):
        from clases.models import Clase, HorarioBase
        inicio, nutri = primera_hora(NUTRICION, self.seguimiento, self.dia)
        base = HorarioBase.objects.first()
        clase = Clase.objects.create(inicio=inicio, sala=base.sala, disciplina=base.disciplina,
                                     instructor=base.instructor, nivel='suave')
        from clases.servicios import reservar
        reservar(self.maria, clase)
        libres = [i for i, _ in horas_libres(NUTRICION, self.seguimiento, self.dia, usuario=self.maria)]
        self.assertNotIn(inicio, libres)


class CancelarTests(TestCase):
    def setUp(self):
        self.maria = cuenta()
        comprar(self.maria, 'atempo-10')
        self.seguimiento = TipoSesion.objects.get(nombre='Seguimiento')

    def test_con_12_horas_devuelve_la_sesion(self):
        dia = proximo(1)
        inicio, nutri = primera_hora(NUTRICION, self.seguimiento, dia)
        cita = agendar(self.maria, nutri, self.seguimiento, inicio)
        self.assertTrue(cancelar_cita(cita))
        self.assertEqual(sesiones_incluidas_disponibles(self.maria, NUTRICION), 1)

    def test_con_menos_de_12_horas_no_devuelve(self):
        nutri = Profesional.objects.get(nombre='Lic. María Becerra')
        inicio = timezone.now() + datetime.timedelta(hours=3)
        cita = Cita.objects.create(usuario=self.maria, profesional=nutri, tipo=self.seguimiento, inicio=inicio,
                                   fin=inicio + datetime.timedelta(minutes=30), forma=Cita.INCLUIDA,
                                   compra=self.maria.compras.first())
        Compra.objects.filter(pk=cita.compra.pk).update(nutricion_usada=1)
        self.assertFalse(cancelar_cita(cita))
        self.assertEqual(sesiones_incluidas_disponibles(self.maria, NUTRICION), 0)

    def test_el_estudio_cancela_y_avisa(self):
        dia = proximo(1)
        inicio, nutri = primera_hora(NUTRICION, self.seguimiento, dia)
        cita = agendar(self.maria, nutri, self.seguimiento, inicio)
        self.assertTrue(cancelar_cita(cita, por_el_estudio=True))
        self.assertTrue(self.maria.notificaciones.filter(tipo=Notificacion.CITA_CANCELADA).exists())


class PaginasTests(TestCase):
    def setUp(self):
        self.maria = cuenta()

    def test_bienestar_y_submenu(self):
        respuesta = self.client.get(reverse('bienestar'))
        for texto in ['Bienestar', 'Nutrición', 'Masajes', 'Lic. María Becerra', 'De La Rose',
                      'Incluida en los paquetes desde', 'Sesión adicional: 1 crédito',
                      reverse('bienestar_servicio', args=['nutricion']), reverse('bienestar_servicio', args=['masajes'])]:
            self.assertContains(respuesta, texto)
        self.assertContains(respuesta, 'class="submenu"')

    def test_pagina_de_servicio_con_agenda(self):
        respuesta = self.client.get(reverse('bienestar_servicio', args=['nutricion']),
                                    {'dia': proximo(1).isoformat()})
        for texto in ['Agenda tu cita', 'Me da igual', 'Evaluación y plan personalizado · 45 min', 'Quién te atiende',
                      'hora-libre']:
            self.assertContains(respuesta, texto)

    def test_servicio_inexistente(self):
        self.assertEqual(self.client.get('/bienestar/yoga/').status_code, 404)

    def agendar_url(self, tipo, dia):
        inicio, p = primera_hora(tipo.servicio, tipo, dia, self.maria)
        local = timezone.localtime(inicio)
        return reverse('bienestar_agendar', args=[tipo.servicio]), {
            'tipo': tipo.pk, 'profesional': p.pk, 'inicio': local.strftime('%Y-%m-%dT%H:%M')}

    def test_evaluacion_pide_ficha_con_consentimiento(self):
        comprar(self.maria, 'atempo-5')
        self.client.force_login(self.maria)
        evaluacion = TipoSesion.objects.get(nombre__startswith='Evaluación')
        url, datos = self.agendar_url(evaluacion, proximo(1))
        confirmacion = self.client.get(url, {**datos, 'parcial': 1})
        self.assertContains(confirmacion, 'Antes de tu evaluación')
        self.assertContains(confirmacion, 'Autorizo a Atempo')
        sin_consentimiento = self.client.post(url, {**datos, 'objetivo': 'energia', 'alergias': 'Ninguna'})
        self.assertContains(sin_consentimiento, 'necesitamos tu autorización')
        self.assertFalse(Cita.objects.exists())
        self.client.post(url, {**datos, 'objetivo': 'energia', 'alergias': 'Ninguna', 'consentimiento': 'on'})
        cita = Cita.objects.get()
        self.assertEqual(cita.objetivo, 'energia')
        self.assertIsNotNone(cita.consentimiento_salud)
        self.assertTrue(self.maria.notificaciones.filter(tipo=Notificacion.CITA_CONFIRMADA).exists())

    def test_seguimiento_no_pide_ficha(self):
        comprar(self.maria, 'atempo-5')
        self.client.force_login(self.maria)
        url, datos = self.agendar_url(TipoSesion.objects.get(nombre='Seguimiento'), proximo(1))
        self.assertNotContains(self.client.get(url, {**datos, 'parcial': 1}), 'Antes de tu evaluación')
        respuesta = self.client.post(url, datos, follow=True)
        self.assertContains(respuesta, '¡Listo! Agendaste seguimiento')

    def test_sin_paquete_explica_y_ofrece_paquetes(self):
        self.client.force_login(self.maria)
        url, datos = self.agendar_url(TipoSesion.objects.get(nombre='Descarga muscular'), proximo(1))
        respuesta = self.client.get(url, {**datos, 'parcial': 1})
        self.assertContains(respuesta, 'se habilitan desde')
        self.assertContains(respuesta, 'Atempo 20')
        self.assertContains(respuesta, 'Ver paquetes')

    def test_mi_cuenta_muestra_citas_y_recordatorio(self):
        comprar(self.maria, 'atempo-5')
        nutri = Profesional.objects.get(nombre='Lic. María Becerra')
        inicio = timezone.now() + datetime.timedelta(hours=20)
        Cita.objects.create(usuario=self.maria, profesional=nutri,
                            tipo=TipoSesion.objects.get(nombre='Seguimiento'), inicio=inicio,
                            fin=inicio + datetime.timedelta(minutes=30), forma=Cita.INCLUIDA)
        self.client.force_login(self.maria)
        respuesta = self.client.get(reverse('cuenta'))
        self.assertContains(respuesta, 'Citas y encuentros')
        self.assertContains(respuesta, 'Seguimiento')
        self.assertTrue(self.maria.notificaciones.filter(tipo=Notificacion.CITA_RECORDATORIO).exists())
