import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from compras.models import registrar_compra
from notificaciones.models import Notificacion
from paquetes.models import Paquete

from .models import Encuentro, Inscripcion
from .servicios import (EJEMPLOS, NoSePuedeInscribir, apertura_para, asegurar_encuentros_de_ejemplo, inscribir,
                        motivo_para_no_inscribirse)

Usuario = get_user_model()


def crear_socia(correo='maria@correo.pe', celular='987654321', dni='45678912'):
    return Usuario.objects.create_user(correo, 'Ritmo-propio-2026', nombre='María', apellido='Salas',
                                       celular=celular, dni=dni)


def comprar(usuario, slug):
    return registrar_compra(usuario, Paquete.objects.get(slug=slug), 'yape', '')


def crear_encuentro(dias, cupo=20, **datos):
    """Un encuentro a `dias` días de hoy, a las 18:00."""
    dia = timezone.localdate() + datetime.timedelta(days=dias)
    inicio = timezone.make_aware(datetime.datetime.combine(dia, datetime.time(18, 0)))
    return Encuentro.objects.create(titulo=datos.pop('titulo', 'Coffee de prueba'), tipo='cafe', inicio=inicio,
                                    lugar='Zona social de Atempo', descripcion='Un café.', cupo=cupo, **datos)


class PaginaComunidadTests(TestCase):
    def test_muestra_los_encuentros_de_ejemplo(self):
        respuesta = self.client.get(reverse('comunidad'))
        self.assertEqual(respuesta.status_code, 200)
        for texto in ['Atempo Circle', 'Cómo funciona', 'Con los paquetes más grandes, tu inscripción se abre antes',
                      'Coffee morning de bienvenida', 'Caminata por el Malecón de Miraflores', 'Apuntarme',
                      'Hay cupos', 'Trae a una amiga']:
            self.assertContains(respuesta, texto)

    def test_filtro_por_tipo(self):
        respuesta = self.client.get(reverse('comunidad') + '?tipo=salida')
        self.assertContains(respuesta, 'Caminata por el Malecón')
        self.assertNotContains(respuesta, 'Coffee morning de bienvenida')

    def test_los_ejemplos_se_renuevan_sin_duplicarse(self):
        asegurar_encuentros_de_ejemplo()
        asegurar_encuentros_de_ejemplo()
        self.assertEqual(Encuentro.objects.count(), len(EJEMPLOS))
        # El coffee pasa: se crea el siguiente
        coffee = Encuentro.objects.get(clave_ejemplo='coffee')
        coffee.inicio = timezone.now() - datetime.timedelta(days=1)
        coffee.save()
        asegurar_encuentros_de_ejemplo()
        self.assertEqual(Encuentro.objects.filter(clave_ejemplo='coffee', inicio__gt=timezone.now()).count(), 1)

    def test_inicio_muestra_proximos_encuentros(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'Próximos encuentros')
        self.assertContains(respuesta, 'Coffee morning de bienvenida')
        self.assertContains(respuesta, 'Ver todos los encuentros')

    def test_terminos_con_las_reglas_de_encuentros(self):
        self.assertContains(self.client.get(reverse('terminos')), 'Encuentros de Atempo Circle')


class AccesoTests(TestCase):
    def setUp(self):
        self.maria = crear_socia()
        self.encuentro = crear_encuentro(5)   # abierto para todos los paquetes (el menor abre 8 días antes)

    def test_sin_paquete_o_con_atempo_1_no_tiene_acceso(self):
        self.assertEqual(motivo_para_no_inscribirse(self.maria, self.encuentro), 'SIN_ACCESO')
        comprar(self.maria, 'atempo-1')
        self.assertEqual(motivo_para_no_inscribirse(self.maria, self.encuentro), 'SIN_ACCESO')

    def test_paquete_que_vence_antes_del_encuentro(self):
        compra = comprar(self.maria, 'atempo-5')
        compra.vence = self.encuentro.fecha - datetime.timedelta(days=1)
        compra.save()
        self.assertEqual(motivo_para_no_inscribirse(self.maria, self.encuentro), 'SIN_ACCESO')
        self.client.force_login(self.maria)
        respuesta = self.client.get(reverse('inscribirse', args=[self.encuentro.pk]) + '?parcial=1')
        self.assertContains(respuesta, f'Tu paquete vence el {compra.vence:%d/%m/%Y}, antes de este encuentro')
        self.assertContains(respuesta, 'Ver paquetes')

    def test_sin_puntos_pero_vigente_si_puede(self):
        compra = comprar(self.maria, 'atempo-5')
        compra.creditos_usados = compra.creditos
        compra.save()
        self.assertIsNone(motivo_para_no_inscribirse(self.maria, self.encuentro))


class AperturaEscalonadaTests(TestCase):
    def setUp(self):
        self.maria = crear_socia()
        self.encuentro = crear_encuentro(11)

    def test_cada_paquete_abre_con_su_anticipacion(self):
        comprar(self.maria, 'atempo-5')   # abre 8 días antes: todavía no
        self.assertEqual(motivo_para_no_inscribirse(self.maria, self.encuentro), 'AUN_NO')
        self.assertEqual(apertura_para(self.maria, self.encuentro), self.encuentro.fecha - datetime.timedelta(days=8))
        comprar(self.maria, 'atempo-40')  # abre 14 días antes: ya puede (cuenta el que abre antes)
        self.assertIsNone(motivo_para_no_inscribirse(self.maria, self.encuentro))

    def test_la_tarjeta_muestra_solo_su_fecha_sin_comparar(self):
        comprar(self.maria, 'atempo-5')
        self.client.force_login(self.maria)
        respuesta = self.client.get(reverse('comunidad'))
        apertura = self.encuentro.fecha - datetime.timedelta(days=8)
        self.assertContains(respuesta, f'Inscripción desde el')
        self.assertContains(respuesta, f'{apertura:%d/%m}')
        self.assertContains(respuesta, 'Recordarme')
        self.assertNotContains(respuesta, 'Con Atempo 20')

    def test_no_se_puede_inscribir_antes_de_tiempo(self):
        comprar(self.maria, 'atempo-5')
        with self.assertRaises(NoSePuedeInscribir):
            inscribir(self.maria, self.encuentro)

    def test_recordarme_avisa_una_vez_cuando_se_abre(self):
        comprar(self.maria, 'atempo-5')
        self.client.force_login(self.maria)
        self.client.post(reverse('recordarme', args=[self.encuentro.pk]))
        self.assertContains(self.client.get(reverse('comunidad')), '✓ Te avisaremos')
        self.assertFalse(self.maria.notificaciones.filter(tipo=Notificacion.ENCUENTRO_APERTURA).exists())

        # Se acerca la fecha: ahora la inscripción ya está abierta para Atempo 5
        self.encuentro.inicio -= datetime.timedelta(days=4)
        self.encuentro.save()
        self.client.get(reverse('inicio'))
        self.client.get(reverse('inicio'))
        avisos = self.maria.notificaciones.filter(tipo=Notificacion.ENCUENTRO_APERTURA)
        self.assertEqual(avisos.count(), 1)
        self.assertIn('Ya puedes apuntarte', avisos.get().texto)
        self.assertIn('También te enviamos un correo', avisos.get().texto)

        # Arriba de Comunidad: el aviso con el correo simulado, hasta que se apunte
        respuesta = self.client.get(reverse('comunidad'))
        self.assertContains(respuesta, 'class="aviso-apertura"')
        self.assertContains(respuesta, 'Asunto:</strong> Ya puedes apuntarte a Coffee de prueba')
        self.client.post(reverse('inscribirse', args=[self.encuentro.pk]))
        self.assertNotContains(self.client.get(reverse('comunidad')), 'class="aviso-apertura"')

    def test_el_aviso_aparece_en_la_misma_visita_en_que_se_abre(self):
        comprar(self.maria, 'atempo-5')
        self.client.force_login(self.maria)
        self.client.post(reverse('recordarme', args=[self.encuentro.pk]))
        self.encuentro.inicio -= datetime.timedelta(days=4)
        self.encuentro.save()
        self.assertContains(self.client.get(reverse('comunidad')), 'class="aviso-apertura"')

    def test_recordarme_se_puede_quitar(self):
        comprar(self.maria, 'atempo-5')
        self.client.force_login(self.maria)
        self.client.post(reverse('recordarme', args=[self.encuentro.pk]))
        self.client.post(reverse('recordarme', args=[self.encuentro.pk]))
        self.assertFalse(self.maria.avisos_de_apertura.exists())


class InscripcionTests(TestCase):
    def setUp(self):
        self.maria = crear_socia()
        comprar(self.maria, 'atempo-5')
        self.encuentro = crear_encuentro(3)
        self.client.force_login(self.maria)

    def test_confirmacion_y_apuntarse(self):
        confirmacion = self.client.get(reverse('inscribirse', args=[self.encuentro.pk]) + '?parcial=1')
        self.assertContains(confirmacion, 'Confirma tu asistencia')
        self.assertContains(confirmacion, 'no gasta puntos')

        respuesta = self.client.post(reverse('inscribirse', args=[self.encuentro.pk]), follow=True)
        self.assertContains(respuesta, '¡Listo! Te apuntaste a Coffee de prueba')
        self.assertContains(respuesta, '✓ Estás inscrita')
        self.assertTrue(self.maria.notificaciones.filter(tipo=Notificacion.ENCUENTRO_CONFIRMADO).exists())
        # No gasta puntos
        self.assertEqual(self.maria.compras.get().creditos_usados, 0)
        # Aparece en Mi cuenta
        cuenta = self.client.get(reverse('cuenta'))
        self.assertContains(cuenta, 'id="encuentros"')
        self.assertContains(cuenta, 'Coffee de prueba')

    def test_no_se_repite_ni_pasa_el_cupo(self):
        inscribir(self.maria, self.encuentro)
        self.assertEqual(motivo_para_no_inscribirse(self.maria, self.encuentro), 'Ya estás inscrita en este encuentro.')
        lleno = crear_encuentro(4, cupo=1, titulo='Taller lleno')
        ana = crear_socia('ana@correo.pe', '912345678', '12345678')
        comprar(ana, 'atempo-5')
        inscribir(ana, lleno)
        self.assertEqual(motivo_para_no_inscribirse(self.maria, lleno), 'Este encuentro está lleno.')
        self.assertContains(self.client.get(reverse('comunidad')), 'Lleno')

    def test_cancelar_hasta_que_empiece(self):
        inscripcion = inscribir(self.maria, self.encuentro)
        self.client.post(reverse('cancelar_inscripcion', args=[inscripcion.pk]))
        inscripcion.refresh_from_db()
        self.assertTrue(inscripcion.cancelada)
        # Puede volver a apuntarse
        otra = inscribir(self.maria, self.encuentro)
        # Ya empezó: no se puede cancelar
        self.encuentro.inicio = timezone.now() - datetime.timedelta(minutes=10)
        self.encuentro.save()
        self.client.post(reverse('cancelar_inscripcion', args=[otra.pk]))
        otra.refresh_from_db()
        self.assertFalse(otra.cancelada)

    def test_recordatorio_24_horas_antes(self):
        cercano = crear_encuentro(0, titulo='Charla de hoy')
        cercano.inicio = timezone.now() + datetime.timedelta(hours=5)
        cercano.save()
        inscribir(self.maria, cercano)
        self.client.get(reverse('inicio'))
        self.client.get(reverse('inicio'))
        self.assertEqual(self.maria.notificaciones.filter(tipo=Notificacion.ENCUENTRO_RECORDATORIO).count(), 1)

    def test_el_estudio_cancela_el_encuentro(self):
        inscribir(self.maria, self.encuentro)
        admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave', nombre='Admin', apellido='Atempo')
        self.client.force_login(admin)
        self.client.post('/admin/comunidad/encuentro/', {'action': 'cancelar_por_estudio',
                                                          '_selected_action': [self.encuentro.pk]})
        self.encuentro.refresh_from_db()
        self.assertTrue(self.encuentro.cancelado)
        self.assertFalse(Inscripcion.objects.filter(cancelada=False).exists())
        self.assertTrue(self.maria.notificaciones.filter(tipo=Notificacion.ENCUENTRO_CANCELADO).exists())

    def test_reiniciar_cuenta_borra_los_encuentros(self):
        from cuentas.admin import reiniciar_cuenta
        inscribir(self.maria, self.encuentro)
        reiniciar_cuenta(self.maria)
        self.assertFalse(self.maria.inscripciones.exists())
