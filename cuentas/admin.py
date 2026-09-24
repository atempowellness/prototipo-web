from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from compras.models import Compra, ajustar_creditos, creditos_disponibles

from .models import Usuario


class UsuarioCreacionForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'apellido', 'celular', 'dni']
        field_classes = {}


class UsuarioCambioForm(UserChangeForm):
    # Ajuste manual de créditos (no se guarda en la cuenta: crea o descuenta créditos)
    ajuste_creditos = forms.IntegerField(
        label='Ajustar créditos', required=False,
        help_text='Escribe, por ejemplo, 2 para sumar dos créditos o -1 para quitar uno. '
                  'Al quitar, se descuentan de los que vencen antes. Déjalo vacío si no quieres ajustar.')
    ajuste_vence = forms.DateField(
        label='Vigencia de los créditos sumados', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Solo al sumar. Si lo dejas vacío, vencen en 1 mes.')
    ajuste_motivo = forms.CharField(
        label='Motivo del ajuste', required=False, max_length=60,
        help_text='Opcional; la clienta lo verá en su aviso (por ejemplo, "compensación por clase cancelada").')

    class Meta:
        model = Usuario
        fields = '__all__'
        field_classes = {}

    def clean_ajuste_creditos(self):
        cantidad = self.cleaned_data.get('ajuste_creditos')
        if cantidad and cantidad < 0 and self.instance.pk and -cantidad > creditos_disponibles(self.instance):
            raise forms.ValidationError(
                f'No se pueden quitar {-cantidad}: la cuenta solo tiene {creditos_disponibles(self.instance)} '
                f'créditos disponibles.')
        return cantidad


class CreditosEnLinea(admin.TabularInline):
    """Detalle de compras, regalos y ajustes de la cuenta (para editarlos, entra a cada uno)."""
    model = Compra
    fk_name = 'usuario'
    verbose_name, verbose_name_plural = 'registro de créditos', 'detalle de créditos (compras, regalos y ajustes)'
    fields = ['tipo', 'nombre_paquete', 'fecha', 'vence', 'creditos', 'creditos_usados', 'disponibles']
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ['-fecha']

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='disponibles')
    def disponibles(self, compra):
        return compra.creditos_disponibles if compra.vigente else '0 (vencido)'


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioCambioForm
    add_form = UsuarioCreacionForm
    inlines = [CreditosEnLinea]
    ordering = ['-date_joined']
    list_display = ['email', 'nombre', 'apellido', 'celular', 'dni', 'creditos', 'codigo_referida',
                    'referida_por', 'date_joined', 'is_staff']
    search_fields = ['email', 'nombre', 'apellido', 'celular', 'dni', 'codigo_referida']
    readonly_fields = ['date_joined', 'last_login', 'acepto_privacidad', 'codigo_referida', 'creditos']
    autocomplete_fields = ['referida_por']
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Datos personales', {'fields': ['nombre', 'apellido', 'celular', 'dni', 'acepto_privacidad']}),
        ('Créditos', {'fields': ['creditos', 'ajuste_creditos', 'ajuste_vence', 'ajuste_motivo']}),
        ('Programa de referidas', {'fields': ['codigo_referida', 'referida_por']}),
        ('Permisos', {'fields': ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']}),
        ('Fechas', {'fields': ['last_login', 'date_joined']}),
    ]
    add_fieldsets = [
        (None, {'classes': ['wide'], 'fields': ['email', 'nombre', 'apellido', 'celular', 'dni', 'password1', 'password2']}),
    ]

    @admin.display(description='créditos disponibles')
    def creditos(self, usuario):
        return creditos_disponibles(usuario)

    def save_model(self, request, usuario, form, change):
        super().save_model(request, usuario, form, change)
        cantidad = form.cleaned_data.get('ajuste_creditos') if change else None
        if not cantidad:
            return
        from notificaciones import avisos

        motivo = form.cleaned_data.get('ajuste_motivo', '')
        ajustados = ajustar_creditos(usuario, cantidad, form.cleaned_data.get('ajuste_vence'), motivo)
        if ajustados:
            avisos.ajuste_de_creditos(usuario, ajustados, motivo)
            n = abs(ajustados)
            if n == 1:
                accion = 'Se sumó 1 crédito' if ajustados > 0 else 'Se quitó 1 crédito'
            else:
                accion = f'Se sumaron {n} créditos' if ajustados > 0 else f'Se quitaron {n} créditos'
            total = creditos_disponibles(usuario)
            self.message_user(request, f'{accion}. La cuenta tiene ahora {total} '
                                       f'{"crédito disponible" if total == 1 else "créditos disponibles"}.',
                              messages.SUCCESS)
