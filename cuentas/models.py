from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

validar_celular = RegexValidator(r'^9\d{8}$', 'Ingresa un celular de 9 dígitos que empiece con 9.')
validar_dni = RegexValidator(r'^\d{8}$', 'Ingresa un DNI de 8 dígitos.')


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

    def get_full_name(self):
        return f'{self.nombre} {self.apellido}'

    def get_short_name(self):
        return self.nombre
