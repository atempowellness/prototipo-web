from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notificaciones.models import Notificacion

from .models import Reclamacion

Usuario = get_user_model()

DATOS = {
    'nombre': 'María Salas', 'dni': '45678912', 'domicilio': 'Av. Ejemplo 123, San Isidro',
    'telefono': '987 654 321', 'email': 'maria@correo.pe', 'servicio': 'clase', 'monto': '',
    'descripcion_servicio': 'Clase de Pilates del 25/09', 'tipo': 'reclamo',
    'detalle': 'La clase empezó 20 minutos tarde.', 'pedido': 'Que me devuelvan el punto.', 'acepto': 'on',
}


class PaginasLegalesTests(TestCase):
    def test_privacidad(self):
        respuesta = self.client.get(reverse('privacidad'))
        for texto in ['Política de privacidad', 'Texto de ejemplo para el prototipo', 'Ley N.° 29733',
                      'datos sensibles', 'consentimiento expreso', 'Atempo Wellness S.A.C.', 'hola@atempo.pe',
                      'Contenido']:
            self.assertContains(respuesta, texto)

    def test_terminos_con_las_reglas_de_atempo(self):
        respuesta = self.client.get(reverse('terminos'))
        for texto in ['1 punto equivale a 1 clase', '12 horas o más', 'Atempo 5', 'hasta 5 puntos de regalo por mes',
                      'Texto de ejemplo para el prototipo']:
            self.assertContains(respuesta, texto)

    def test_pie_con_icono_del_libro(self):
        self.assertContains(self.client.get(reverse('inicio')), 'class="enlace-libro"')


class LibroDeReclamacionesTests(TestCase):
    def test_formulario_con_los_campos_de_la_hoja(self):
        respuesta = self.client.get(reverse('reclamaciones'))
        for texto in ['Hoja de reclamación', 'Reclamo:', 'Queja:', '15 días hábiles', 'Tus datos',
                      'Servicio contratado', 'Detalle', 'INDECOPI']:
            self.assertContains(respuesta, texto)

    def test_con_sesion_se_llenan_los_datos(self):
        maria = Usuario.objects.create_user('maria@correo.pe', 'Ritmo-propio-2026', nombre='María',
                                            apellido='Salas', celular='987654321', dni='45678912')
        self.client.force_login(maria)
        respuesta = self.client.get(reverse('reclamaciones'))
        self.assertContains(respuesta, 'value="45678912"')
        self.assertContains(respuesta, 'value="María Salas"')

    def test_enviar_crea_la_hoja_numerada(self):
        respuesta = self.client.post(reverse('reclamaciones'), DATOS, follow=True)
        self.assertEqual(respuesta.redirect_chain[-1][0], reverse('reclamaciones') + '?enviada=1')
        anio = timezone.localdate().year
        self.assertContains(respuesta, f'N.° {anio}-0001')
        self.assertContains(respuesta, 'así se vería la constancia')
        self.client.post(reverse('reclamaciones'), {**DATOS, 'tipo': 'queja'})
        self.assertEqual(Reclamacion.objects.order_by('pk').last().numero, f'{anio}-0002')

    def test_otra_persona_no_ve_la_constancia(self):
        self.client.post(reverse('reclamaciones'), DATOS)
        otro = self.client_class()
        self.assertNotContains(otro.get(reverse('reclamaciones') + '?enviada=1'), 'María Salas')

    def test_errores(self):
        respuesta = self.client.post(reverse('reclamaciones'), {**DATOS, 'dni': '123', 'acepto': ''})
        self.assertContains(respuesta, 'Ingresa un DNI de 8 dígitos')
        self.assertContains(respuesta, 'confirmar que los datos son verdaderos')
        self.assertFalse(Reclamacion.objects.exists())

    def test_aviso_al_recibir_y_al_responder(self):
        maria = Usuario.objects.create_user('maria@correo.pe', 'Ritmo-propio-2026', nombre='María',
                                            apellido='Salas', celular='987654321', dni='45678912')
        self.client.force_login(maria)
        self.client.post(reverse('reclamaciones'), DATOS)
        self.assertTrue(maria.notificaciones.filter(texto__startswith='Recibimos tu reclamo').exists())

        admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave', nombre='Admin', apellido='Atempo')
        self.client.force_login(admin)
        hoja = Reclamacion.objects.get()
        self.client.post(f'/admin/legal/reclamacion/{hoja.pk}/change/',
                         {'estado': 'respondida', 'respuesta': 'Te devolvimos el punto.'})
        hoja.refresh_from_db()
        self.assertIsNotNone(hoja.respondida_en)
        self.assertTrue(maria.notificaciones.filter(texto__startswith='Respondimos tu reclamo').exists())

        # Los dos avisos llevan a la sección de reclamos de Mi cuenta
        destinos = set(maria.notificaciones.filter(tipo=Notificacion.RECLAMACION).values_list('enlace', flat=True))
        self.assertEqual(destinos, {reverse('cuenta') + '#reclamos'})

        # El panel muestra el estado con color
        self.assertContains(self.client.get('/admin/legal/reclamacion/'), 'estado estado-respondida')

        # En Mi cuenta aparece la hoja con la respuesta
        self.client.force_login(maria)
        respuesta = self.client.get(reverse('cuenta'))
        self.assertContains(respuesta, 'id="reclamos"')
        self.assertContains(respuesta, f'Hoja N.° {hoja.numero}')
        self.assertContains(respuesta, 'estado-hoja-respondida')
        self.assertContains(respuesta, 'Te devolvimos el punto.')

    def test_sin_reclamos_no_aparece_la_seccion(self):
        maria = Usuario.objects.create_user('maria@correo.pe', 'Ritmo-propio-2026', nombre='María',
                                            apellido='Salas', celular='987654321', dni='45678912')
        self.client.force_login(maria)
        self.assertNotContains(self.client.get(reverse('cuenta')), 'id="reclamos"')

    def test_quitar_de_mi_cuenta_solo_si_esta_respondida(self):
        maria = Usuario.objects.create_user('maria@correo.pe', 'Ritmo-propio-2026', nombre='María',
                                            apellido='Salas', celular='987654321', dni='45678912')
        self.client.force_login(maria)
        self.client.post(reverse('reclamaciones'), DATOS)
        hoja = Reclamacion.objects.get()
        url = reverse('quitar_reclamacion', args=[hoja.pk])

        # Pendiente: no hay botón y no se puede quitar
        self.assertNotContains(self.client.get(reverse('cuenta')), url)
        self.assertEqual(self.client.post(url).status_code, 404)

        hoja.estado, hoja.respuesta = Reclamacion.RESPONDIDA, 'Te devolvimos el punto.'
        hoja.save()
        self.assertContains(self.client.get(reverse('cuenta')), url)
        self.assertContains(self.client.get(url + '?parcial=1'), '¿Quitar esta hoja de tu cuenta?')

        # Otra clienta no puede quitarla
        otra = Usuario.objects.create_user('ana@correo.pe', 'Ritmo-propio-2026', nombre='Ana',
                                           apellido='Ríos', celular='912345678', dni='12345678')
        self.client.force_login(otra)
        self.assertEqual(self.client.post(url).status_code, 404)

        # Al quitarla, la sección desaparece, pero la hoja se conserva para el estudio
        self.client.force_login(maria)
        self.client.post(url)
        self.assertNotContains(self.client.get(reverse('cuenta')), 'id="reclamos"')
        hoja.refresh_from_db()
        self.assertTrue(hoja.quitada_por_clienta)

    def test_boton_de_datos_de_prueba(self):
        self.assertContains(self.client.get(reverse('reclamaciones')), 'data-datos-prueba-reclamo')
