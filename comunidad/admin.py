from django.contrib import admin, messages
from django.utils import timezone

from core.admin import EliminarSoloPruebasMixin

from .models import Encuentro, Inscripcion
from .servicios import cancelar_encuentro_por_estudio, cancelar_inscripcion


@admin.action(description='Cancelar los encuentros seleccionados (avisa a las inscritas)')
def cancelar_por_estudio(modeladmin, request, queryset):
    total_encuentros, total_inscritas = 0, 0
    for encuentro in queryset.filter(cancelado=False, inicio__gt=timezone.now()):
        total_inscritas += cancelar_encuentro_por_estudio(encuentro)
        total_encuentros += 1
    modeladmin.message_user(
        request, f'Encuentros cancelados: {total_encuentros}. Socias avisadas: {total_inscritas}.', messages.SUCCESS)


class InscripcionEnLinea(admin.TabularInline):
    model = Inscripcion
    extra = 0
    fields = ['usuario', 'creada', 'cancelada']
    readonly_fields = fields
    can_delete = False
    verbose_name_plural = 'asistentes'


@admin.register(Encuentro)
class EncuentroAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'inicio', 'lugar', 'inscritas', 'cupo', 'cancelado']
    list_filter = ['tipo', 'cancelado']
    date_hierarchy = 'inicio'
    search_fields = ['titulo', 'lugar']
    actions = [cancelar_por_estudio]
    inlines = [InscripcionEnLinea]
    readonly_fields = ['cancelado']
    fieldsets = [
        (None, {'fields': ['titulo', 'tipo', 'descripcion']}),
        ('Cuándo y dónde', {'fields': ['inicio', 'duracion_minutos', 'lugar']}),
        ('Cupo', {'fields': ['cupo', 'cancelado'],
                  'description': 'La inscripción se abre según el paquete de cada socia (panel → Paquetes → '
                                 '"inscripción a encuentros"). Para cancelar un encuentro, usa la acción '
                                 '"Cancelar los encuentros seleccionados" en la lista: avisa a las inscritas.'}),
    ]

    @admin.display(description='inscritas')
    def inscritas(self, encuentro):
        return encuentro.inscripciones_activas().count()


@admin.action(description='Cancelar las asistencias seleccionadas (avisa a la socia)')
def cancelar_inscripciones_por_estudio(modeladmin, request, queryset):
    total = 0
    for inscripcion in queryset.filter(cancelada=False).select_related('encuentro', 'usuario'):
        cancelar_inscripcion(inscripcion, por_el_estudio=True)
        total += 1
    texto = '1 asistencia cancelada' if total == 1 else f'{total} asistencias canceladas'
    modeladmin.message_user(request, f'{texto}, con aviso a la socia.', messages.SUCCESS)


@admin.register(Inscripcion)
class InscripcionAdmin(EliminarSoloPruebasMixin, admin.ModelAdmin):
    actions = [cancelar_inscripciones_por_estudio]
    list_display = ['encuentro', 'usuario', 'creada', 'cancelada']
    list_filter = ['cancelada', 'encuentro__tipo']
    search_fields = ['usuario__email', 'usuario__nombre', 'usuario__apellido', 'encuentro__titulo']
    readonly_fields = ['usuario', 'encuentro', 'creada', 'cancelada', 'cancelada_en']
