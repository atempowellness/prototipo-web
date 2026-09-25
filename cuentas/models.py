import random
import re
import unicodedata

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

validar_celular = RegexValidator(r'^9\d{8}$', 'Ingresa un celular de 9 dígitos que empiece con 9.')
validar_dni = RegexValidator(r'^\d{8}$', 'Ingresa un DNI de 8 dígitos.')

# Caracteres del código de referida: sin 0/O ni 1/I, que se confunden al dictarlos
CARACTERES_CODIGO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generar_codigo_referida(nombre):
    """'María José' -> 'MARIA-7K3Q' (primer nombre sin tildes + 4 caracteres al azar)."""
    sin_tildes = unicodedata.normalize('NFKD', nombre or '').encode('ascii', 'ignore').decode()
    palabras = re.findall(r'[A-Za-z]+', sin_tildes)
    base = (palabras[0] if palabras else 'ATEMPO').upper()[:10]
    while True:
        codigo = f'{base}-' + ''.join(random.choices(CARACTERES_CODIGO, k=4))
        if not Usuario.objects.filter(codigo_referida=codigo).exists():
            return codigo


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **datos):
        if not email:
            raise ValueError('La cuenta necesita un correo.')
        usuario = self.model(email=self.normalize_email(email).lower(), **datos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **datos):
        datos.setdefault('is_staff', True)
        datos.setdefault('is_superuser', True)
        return self.create_user(email, password, **datos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Cuenta de Atempo. Se ingresa con el correo o el celular, más la contraseña.
    El celular y el DNI son obligatorios al registrarse en la web; en las cuentas
    de administración creadas con "createsuperuser" pueden quedar vacíos.
    """
    email = models.EmailField('correo electrónico', unique=True)
    nombre = models.CharField(max_length=60)
    apellido = models.CharField(max_length=60)
    celular = models.CharField(max_length=9, unique=True, null=True, blank=True, validators=[validar_celular])
    dni = models.CharField('DNI', max_length=8, unique=True, null=True, blank=True, validators=[validar_dni])
    acepto_privacidad = models.DateTimeField(
        'aceptó la política de privacidad', null=True, blank=True,
        help_text='Fecha y hora en que aceptó el tratamiento de sus datos (Ley N.° 29733).',
    )

    # Programa de referidas
    codigo_referida = models.CharField(
        'código de referida', max_length=16, unique=True, blank=True,
        help_text='Su código personal para invitar amigas. Se crea solo.')
    referida_por = models.ForeignKey(
        'self', verbose_name='invitada por', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='invitadas', help_text='Quién la invitó. Cada cuenta puede usar un solo código.')

    is_active = models.BooleanField('activa', default=True)
    is_staff = models.BooleanField('acceso al panel de administración', default=False)
    date_joined = models.DateTimeField('fecha de registro', default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    class Meta:
        # En masculino porque las frases del panel de administración vienen
        # traducidas así ("el usuario seleccionado"); con "cuenta" salía "el cuenta".
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def __str__(self):
        return f'{self.nombre} {self.apellido} ({self.email})'

    def save(self, *args, **kwargs):
        if not self.codigo_referida:
            self.codigo_referida = generar_codigo_referida(self.nombre)
        super().save(*args, **kwargs)

    @property
    def nombre_corto(self):
        """'Ana Paz' -> 'Ana P.' (para mostrar a otras clientas sin el apellido completo)."""
        return f'{self.nombre} {self.apellido[:1]}.' if self.apellido else self.nombre

    def get_full_name(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def compra_founding(self):
        """Su compra del paquete Founding Members, o None."""
        return self.compras.filter(tipo='compra', paquete__es_founding=True).first()

    @property
    def es_founding(self):
        return self.compra_founding is not None

    @property
    def numero_founding(self):
        """Su número de fundadora: 1 = la primera en comprar Founding Members."""
        compra = self.compra_founding
        if compra is None:
            return None
        anteriores = compra.paquete.compras.filter(tipo='compra', fecha__lt=compra.fecha).count()
        return anteriores + 1

    @property
    def es_demostracion(self):
        """¿Es la cuenta de demostración del prototipo? (ver cuentas/demostracion.py)."""
        from .demostracion import CORREO_DEMO
        return self.email == CORREO_DEMO

    def get_short_name(self):
        return self.nombre
