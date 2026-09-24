from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

Usuario = get_user_model()

DATOS_VALIDOS = {
    'nombre': 'María', 'apellido': 'Salas', 'email': 'Maria.Salas@Correo.pe',
    'celular': '987 654 321', 'dni': '45678912',
    'password1': 'Ritmo-propio-2026', 'password2': 'Ritmo-propio-2026',
    'acepto_privacidad': 'on',
}


def crear_maria():
    return Usuario.objects.create_user(
        'maria@correo.pe', 'Ritmo-propio-2026',
        nombre='María', apellido='Salas', celular='987654321', dni='45678912',
    )


class RegistroTests(TestCase):
    def test_registro_crea_la_cuenta_e_inicia_sesion(self):
        respuesta = self.client.post(reverse('registro'), DATOS_VALIDOS, follow=True)
        usuario = Usuario.objects.get()
        self.assertEqual(usuario.email, 'maria.salas@correo.pe')   # se guarda en minúsculas
        self.assertEqual(usuario.celular, '987654321')             # se guardan solo los dígitos
        self.assertIsNotNone(usuario.acepto_privacidad)
        self.assertTrue(respuesta.context['user'].is_authenticated)
        self.assertContains(respuesta, '¡Hola, María!')              # llega a Mi cuenta
        self.assertContains(respuesta, '¡Bienvenida a Atempo, María!')

    def test_vuelve_a_la_pagina_de_donde_venia(self):
        respuesta = self.client.post(reverse('registro') + '?next=/paquetes/',
                                     {**DATOS_VALIDOS, 'next': '/paquetes/'})
        self.assertRedirects(respuesta, '/paquetes/')

    def test_no_redirige_a_otros_sitios(self):
        respuesta = self.client.post(reverse('registro'), {**DATOS_VALIDOS, 'next': 'https://otro-sitio.com/'})
        self.assertRedirects(respuesta, reverse('cuenta'))

    def test_errores_claros(self):
        casos = {
            'celular': ('812345678', 'Ingresa un celular de 9 dígitos que empiece con 9.'),
            'dni': ('1234', 'Ingresa un DNI de 8 dígitos.'),
            'password2': ('otra-clave-2026', 'Las contraseñas no coinciden.'),
            'acepto_privacidad': ('', 'Para crear tu cuenta necesitas aceptar la política de privacidad.'),
        }
        for campo, (valor, mensaje) in casos.items():
            with self.subTest(campo=campo):
                datos = {**DATOS_VALIDOS, campo: valor}
                respuesta = self.client.post(reverse('registro'), datos)
                self.assertContains(respuesta, mensaje)
                self.assertFalse(Usuario.objects.exists())

    def test_no_repite_correo_celular_ni_dni(self):
        crear_maria()
        respuesta = self.client.post(reverse('registro'), {**DATOS_VALIDOS, 'email': 'MARIA@correo.pe'})
        self.assertContains(respuesta, 'Ya existe una cuenta con este correo')
        self.assertContains(respuesta, 'Ya existe una cuenta con este celular')
        self.assertContains(respuesta, 'Ya existe una cuenta con este DNI')
        self.assertEqual(Usuario.objects.count(), 1)

    def test_contrasena_debil_rechazada(self):
        respuesta = self.client.post(reverse('registro'), {**DATOS_VALIDOS, 'password1': '12345678', 'password2': '12345678'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.exists())


class IngresarTests(TestCase):
    def setUp(self):
        crear_maria()

    def test_ingresa_con_correo(self):
        respuesta = self.client.post(reverse('ingresar'), {'username': 'MARIA@correo.pe', 'password': 'Ritmo-propio-2026'})
        self.assertRedirects(respuesta, reverse('cuenta'))

    def test_ingresa_con_celular_con_espacios(self):
        respuesta = self.client.post(reverse('ingresar'), {'username': '987 654 321', 'password': 'Ritmo-propio-2026'})
        self.assertRedirects(respuesta, reverse('cuenta'))

    def test_clave_incorrecta(self):
        respuesta = self.client.post(reverse('ingresar'), {'username': 'maria@correo.pe', 'password': 'equivocada'})
        self.assertContains(respuesta, 'no son correctos')

    def test_titulo(self):
        self.assertContains(self.client.get(reverse('ingresar')), '¡Hola de nuevo!')

    def test_vuelve_a_paquetes(self):
        respuesta = self.client.post(reverse('ingresar'),
                                     {'username': 'maria@correo.pe', 'password': 'Ritmo-propio-2026', 'next': '/paquetes/'})
        self.assertRedirects(respuesta, '/paquetes/')


class MiCuentaTests(TestCase):
    def test_sin_sesion_pide_ingresar(self):
        respuesta = self.client.get(reverse('cuenta'))
        self.assertRedirects(respuesta, reverse('ingresar') + '?next=/cuenta/')

    def test_muestra_datos_y_espacios_pendientes(self):
        self.client.force_login(crear_maria())
        respuesta = self.client.get(reverse('cuenta'))
        for texto in ['¡Hola, María!', 'maria@correo.pe', '987654321', '45678912',
                      'Créditos disponibles', 'Próximamente', 'Cerrar sesión']:
            self.assertContains(respuesta, texto)
        # El encabezado ya dice "Mi cuenta" en lugar de "Ingresar"
        self.assertContains(respuesta, '>Mi cuenta</a>')

    def test_cerrar_sesion(self):
        self.client.force_login(crear_maria())
        respuesta = self.client.post(reverse('salir'), follow=True)
        self.assertFalse(respuesta.context['user'].is_authenticated)
        self.assertContains(respuesta, 'Cerraste sesión')


class RecuperarTests(TestCase):
    def test_flujo_completo_con_correo_simulado(self):
        crear_maria()
        respuesta = self.client.post(reverse('recuperar'), {'email': 'maria@correo.pe'})
        self.assertContains(respuesta, 'Simulación del prototipo')
        ruta = respuesta.context['correo_simulado']['ruta']

        # El enlace lleva a crear la nueva contraseña
        pagina = self.client.get(ruta, follow=True)
        self.assertContains(pagina, 'Crea tu nueva contraseña')
        final = self.client.post(pagina.redirect_chain[-1][0], {
            'new_password1': 'Nuevo-ritmo-2027', 'new_password2': 'Nuevo-ritmo-2027'}, follow=True)
        self.assertContains(final, 'tu contraseña cambió')
        self.assertTrue(self.client.login(username='maria@correo.pe', password='Nuevo-ritmo-2027'))

    def test_correo_no_registrado(self):
        respuesta = self.client.post(reverse('recuperar'), {'email': 'nadie@correo.pe'})
        self.assertContains(respuesta, 'No encontramos una cuenta')
        self.assertNotContains(respuesta, 'Simulación del prototipo')


class PanelAdministracionTests(TestCase):
    """Las frases de "eliminar seleccionados" deben ir en singular o plural según corresponda."""

    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin@atempo.pe', 'clave-de-prueba', nombre='Admin', apellido='Atempo')
        self.maria = crear_maria()
        self.ana = Usuario.objects.create_user('ana@correo.pe', 'Ritmo-propio-2026', nombre='Ana', apellido='Paz',
                                               celular='912345678', dni='12345678')
        self.client.force_login(self.admin)

    def eliminar(self, ids, confirmar=False):
        datos = {'action': 'delete_selected', '_selected_action': ids}
        if confirmar:
            datos['post'] = 'yes'
        return self.client.post('/admin/cuentas/usuario/', datos, follow=confirmar)

    def test_menu_de_acciones(self):
        respuesta = self.client.get('/admin/cuentas/usuario/')
        self.assertContains(respuesta, 'Eliminar usuarios seleccionados')
        self.assertNotContains(respuesta, 'seleccionado/s')

    def test_confirmacion_en_singular(self):
        respuesta = self.eliminar([self.maria.pk])
        self.assertContains(respuesta, '¿Seguro que quieres eliminar el usuario seleccionado?')

    def test_confirmacion_en_plural(self):
        respuesta = self.eliminar([self.maria.pk, self.ana.pk])
        self.assertContains(respuesta, '¿Seguro que quieres eliminar los 2 usuarios seleccionados?')
        self.assertNotContains(respuesta, 'el usuarios')

    def test_mensaje_final_en_singular_y_plural(self):
        respuesta = self.eliminar([self.maria.pk], confirmar=True)
        self.assertContains(respuesta, 'Se eliminó 1 usuario correctamente.')
        respuesta = self.eliminar([self.ana.pk, self.admin.pk], confirmar=True)
        self.assertContains(respuesta, 'Se eliminaron 2 usuarios correctamente.')

    def test_paquetes_tambien(self):
        respuesta = self.client.get('/admin/paquetes/paquete/')
        self.assertContains(respuesta, 'Eliminar paquetes seleccionados')


class PaquetesConSesionTests(TestCase):
    def test_boton_comprar_segun_sesion(self):
        # Sin sesión: primero ingresar, luego directo al pago
        respuesta = self.client.get(reverse('paquetes'))
        self.assertContains(respuesta, '/cuenta/ingresar/?next=/paquetes/atempo-10/comprar/')
        # Con sesión: directo al pago
        self.client.force_login(crear_maria())
        respuesta = self.client.get(reverse('paquetes'))
        self.assertContains(respuesta, 'href="/paquetes/atempo-10/comprar/">Comprar</a>')
