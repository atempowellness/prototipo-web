from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from compras.models import Compra, ajustar_creditos, creditos_disponibles

from .models import Usuario


class UsuarioCreacionForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'apellido', 'celular', 'dni']
        field_classes = {}


class UsuarioCambioForm(UserChangeForm):
    # Ajuste manual de puntos (no se guarda en la cuenta: crea o descuenta puntos)
    ajuste_creditos = forms.IntegerField(
        label='Ajustar puntos', required=False,
        help_text='Escribe, por ejemplo, 2 para sumar dos puntos o -1 para quitar uno. '
                  'Al quitar, se descuentan de los que vencen antes. Déjalo vacío si no quieres ajustar.')
    ajuste_vence = forms.DateField(
        label='Vigencia de los puntos sumados', required=False,
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
                f'puntos disponibles.')
        return cantidad


class CreditosEnLinea(admin.TabularInline):
    """Detalle de compras, regalos y ajustes de la cuenta (para editarlos, entra a cada uno)."""
    model = Compra
    fk_name = 'usuario'
    verbose_name, verbose_name_plural = 'registro de puntos', 'detalle de puntos (compras, regalos y ajustes)'
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


def reiniciar_cuenta(usuario):
    """
    SOLO PARA PRUEBAS. Deja la cuenta como recién creada: borra sus pagos (con regalos y
    ajustes), reservas de clases, citas, encuentros y notificaciones. No toca sus datos
    personales, su contraseña, su código de referida ni quién la invitó.
    Devuelve cuántos registros borró de cada tipo.
    """
    conteo = {
        'reservas': usuario.reservas.count(),
        'citas': usuario.citas.count(),
        'encuentros': usuario.inscripciones.count(),
        'pagos': usuario.compras.count(),
        'avisos': usuario.notificaciones.count(),
    }
    usuario.reservas.all().delete()
    usuario.citas.all().delete()
    usuario.inscripciones.all().delete()
    usuario.avisos_de_apertura.all().delete()
    usuario.compras.all().delete()
    usuario.notificaciones.all().delete()
    return conteo


@admin.action(description='Reiniciar cuentas de prueba (borra pagos, puntos, reservas, citas, encuentros y avisos)')
def reiniciar_cuentas(modeladmin, request, queryset):
    ids = ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))
    return redirect(reverse('admin:cuentas_usuario_reiniciar') + f'?ids={ids}')


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    actions = [reiniciar_cuentas]
    change_form_template = 'admin/cuentas/usuario/change_form.html'

    def get_urls(self):
        propias = [path('reiniciar/', self.admin_site.admin_view(self.vista_reiniciar),
                        name='cuentas_usuario_reiniciar')]
        return propias + super().get_urls()

    def vista_reiniciar(self, request):
        """Pantalla de confirmación y, al confirmar, el reinicio de las cuentas elegidas."""
        ids = [int(x) for x in (request.POST.get('ids') or request.GET.get('ids', '')).split(',') if x.isdigit()]
        usuarios = list(Usuario.objects.filter(pk__in=ids))
        lista = reverse('admin:cuentas_usuario_changelist')
        if not usuarios:
            return redirect(lista)
        if request.method == 'POST' and request.POST.get('confirmar'):
            for usuario in usuarios:
                reiniciar_cuenta(usuario)
            nombres = ', '.join(u.get_full_name() for u in usuarios)
            if len(usuarios) == 1:
                texto = f'Cuenta reiniciada: {nombres}. Ya no tiene pagos, puntos, reservas, citas ni avisos.'
            else:
                texto = f'{len(usuarios)} cuentas reiniciadas: {nombres}. Ya no tienen pagos, puntos, reservas, citas ni avisos.'
            self.message_user(request, texto, messages.SUCCESS)
            return redirect(lista if len(usuarios) > 1 else reverse('admin:cuentas_usuario_change', args=[usuarios[0].pk]))
        resumen = [{'usuario': u, 'pagos': u.compras.count(), 'reservas': u.reservas.count(),
                    'citas': u.citas.count(), 'encuentros': u.inscripciones.count(),
                    'avisos': u.notificaciones.count(),
                    'puntos': creditos_disponibles(u)} for u in usuarios]
        contexto = {**self.admin_site.each_context(request), 'title': 'Reiniciar cuenta de prueba',
                    'opts': self.model._meta, 'resumen': resumen, 'ids': ','.join(str(u.pk) for u in usuarios),
                    'volver': request.GET.get('volver') or lista}
        return TemplateResponse(request, 'admin/cuentas/usuario/reiniciar.html', contexto)
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
        ('Puntos', {'fields': ['creditos', 'ajuste_creditos', 'ajuste_vence', 'ajuste_motivo']}),
        ('Programa de referidas', {'fields': ['codigo_referida', 'referida_por']}),
        ('Permisos', {'fields': ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']}),
        ('Fechas', {'fields': ['last_login', 'date_joined']}),
    ]
    add_fieldsets = [
        (None, {'classes': ['wide'], 'fields': ['email', 'nombre', 'apellido', 'celular', 'dni', 'password1', 'password2']}),
    ]

    @admin.display(description='puntos disponibles')
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
                accion = 'Se sumó 1 punto' if ajustados > 0 else 'Se quitó 1 punto'
            else:
                accion = f'Se sumaron {n} puntos' if ajustados > 0 else f'Se quitaron {n} puntos'
            total = creditos_disponibles(usuario)
            self.message_user(request, f'{accion}. La cuenta tiene ahora {total} '
                                       f'{"punto disponible" if total == 1 else "puntos disponibles"}.',
                              messages.SUCCESS)
