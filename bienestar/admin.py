from django.contrib import admin, messages
from django.utils import timezone

from core.admin import EliminarSoloPruebasMixin

from .models import Cita, HorarioAtencion, TipoSesion
from .servicios import cancelar_cita


@admin.register(TipoSesion)
class TipoSesionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'servicio', 'duracion_minutos', 'pide_ficha', 'orden']
    list_editable = ['duracion_minutos', 'pide_ficha', 'orden']


@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    """Bloques semanales de atención. Las horas libres de la web se calculan a partir de aquí."""
    list_display = ['profesional', 'dia_semana', 'desde', 'hasta', 'activo']
    list_editable = ['desde', 'hasta', 'activo']
    list_filter = ['profesional', 'dia_semana']


@admin.action(description='Cancelar las citas seleccionadas (devuelve la sesión o los puntos y avisa a la clienta)')
def cancelar_por_estudio(modeladmin, request, queryset):
    total = 0
    for cita in queryset.filter(cancelada=False):
        cancelar_cita(cita, por_el_estudio=True)
        total += 1
    texto = '1 cita cancelada' if total == 1 else f'{total} citas canceladas'
    modeladmin.message_user(request, f'{texto}, con la sesión o los puntos devueltos y aviso a la clienta.',
                            messages.SUCCESS)


@admin.register(Cita)
class CitaAdmin(EliminarSoloPruebasMixin, admin.ModelAdmin):
    list_display = ['inicio', 'tipo', 'profesional', 'usuario', 'forma', 'cancelada']
    list_filter = ['tipo__servicio', 'profesional', 'forma', 'cancelada']
    search_fields = ['usuario__email', 'usuario__nombre', 'usuario__apellido']
    date_hierarchy = 'inicio'
    actions = [cancelar_por_estudio]
    readonly_fields = ['usuario', 'profesional', 'tipo', 'inicio', 'fin', 'forma', 'compra', 'compras_creditos',
                       'creada', 'cancelada', 'cancelada_en', 'devuelta', 'consentimiento_salud']
    fieldsets = [
        ('Cita', {'fields': ['usuario', 'profesional', 'tipo', 'inicio', 'fin']}),
        ('Pago', {'fields': ['forma', 'compra', 'compras_creditos']}),
        ('Ficha de nutrición (datos de salud: uso exclusivo para la asesoría)', {'fields': [
            'objetivo', 'alergias', 'condiciones', 'consentimiento_salud']}),
        ('Estado', {'fields': ['creada', 'cancelada', 'cancelada_en', 'devuelta']}),
    ]
