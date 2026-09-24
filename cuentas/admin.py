from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import Usuario


class UsuarioCreacionForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'apellido', 'celular', 'dni']
        field_classes = {}


class UsuarioCambioForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = '__all__'
        field_classes = {}


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioCambioForm
    add_form = UsuarioCreacionForm
    ordering = ['-date_joined']
    list_display = ['email', 'nombre', 'apellido', 'celular', 'dni', 'codigo_referida', 'referida_por',
                    'date_joined', 'is_staff']
    search_fields = ['email', 'nombre', 'apellido', 'celular', 'dni', 'codigo_referida']
    readonly_fields = ['date_joined', 'last_login', 'acepto_privacidad', 'codigo_referida']
    autocomplete_fields = ['referida_por']
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Datos personales', {'fields': ['nombre', 'apellido', 'celular', 'dni', 'acepto_privacidad']}),
        ('Programa de referidas', {'fields': ['codigo_referida', 'referida_por']}),
        ('Permisos', {'fields': ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']}),
        ('Fechas', {'fields': ['last_login', 'date_joined']}),
    ]
    add_fieldsets = [
        (None, {'classes': ['wide'], 'fields': ['email', 'nombre', 'apellido', 'celular', 'dni', 'password1', 'password2']}),
    ]
