from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Paquete, ahorro_maximo_por_clase, precio_clase_suelta


class CalculosTests(TestCase):
    """Los 5 paquetes iniciales se cargan con la migración 0002."""

    def test_precio_por_clase_y_ahorro(self):
        esperado = {
            'Atempo 1': (Decimal(65), Decimal(0)),
            'Atempo 5': (Decimal(60), Decimal(25)),
            'Atempo 10': (Decimal(57), Decimal(80)),
            'Atempo 20': (Decimal(54), Decimal(220)),
            'Atempo 40': (Decimal(50), Decimal(600)),
        }
        for nombre, (por_clase, ahorro) in esperado.items():
            with self.subTest(paquete=nombre):
                paquete = Paquete.objects.get(nombre=nombre)
                self.assertEqual(paquete.precio_por_clase, por_clase)
                self.assertEqual(paquete.ahorro, ahorro)

    def test_clase_suelta_y_ahorro_maximo(self):
        self.assertEqual(precio_clase_suelta(), Decimal(65))
        self.assertEqual(ahorro_maximo_por_clase(), Decimal(15))

    def test_ahorro_maximo_se_actualiza_al_cambiar_un_precio(self):
        Paquete.objects.filter(nombre='Atempo 40').update(precio=Decimal(1800))  # S/ 45 por clase
        self.assertEqual(ahorro_maximo_por_clase(), Decimal(20))


class PaginaPaquetesTests(TestCase):
    def test_muestra_los_cinco_paquetes(self):
        respuesta = self.client.get(reverse('paquetes'))
        self.assertEqual(respuesta.status_code, 200)
        for texto in ['Paquetes de lanzamiento', 'Atempo 1', 'Atempo 40', 'S/ 1,080',
                      'S/ 54 por clase', 'Ahorras S/ 600', 'Más popular', 'Clase suelta',
                      'Masaje adicional: 2 créditos']:
            self.assertContains(respuesta, texto)

    def test_comprar_lleva_a_iniciar_sesion_y_luego_al_pago(self):
        respuesta = self.client.get(reverse('paquetes'))
        for slug in ['atempo-1', 'atempo-5', 'atempo-10', 'atempo-20', 'atempo-40']:
            self.assertContains(respuesta, f'href="{reverse("ingresar")}?next=/paquetes/{slug}/comprar/">Comprar</a>')

    def test_paquete_inactivo_no_se_muestra(self):
        Paquete.objects.filter(nombre='Atempo 40').update(activo=False)
        respuesta = self.client.get(reverse('paquetes'))
        self.assertNotContains(respuesta, 'Atempo 40')


class InicioUsaLosPreciosTests(TestCase):
    def test_textos_de_precio_en_inicio(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'Ahorra hasta <span class="cifra">S/ 15</span> por clase')
        self.assertContains(respuesta, 'Prueba una clase por S/ 65')
        self.assertContains(
            respuesta,
            '1 mes para <strong class="nombre-marca">Atempo 1</strong> y '
            '<strong class="nombre-marca">Atempo 5</strong>, 2 meses para',
        )

    def test_inicio_cambia_si_cambia_un_precio(self):
        Paquete.objects.filter(nombre='Atempo 40').update(precio=Decimal(1800))
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'Ahorra hasta <span class="cifra">S/ 20</span> por clase')


class PanelAdministracionTests(TestCase):
    def test_paquetes_editables_en_el_panel(self):
        from django.contrib.auth import get_user_model
        admin = get_user_model().objects.create_superuser(
            'admin@example.com', 'clave-de-prueba', nombre='Admin', apellido='Atempo')
        self.client.force_login(admin)
        respuesta = self.client.get('/admin/paquetes/paquete/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Atempo 20')
