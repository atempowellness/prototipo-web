from django.contrib import admin, messages
from django.utils import timezone

from .models import Clase, Disciplina, HorarioBase, Profesional, Reserva, Sala
from .servicios import cancelar_clase_por_estudio, generar_clases


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden']
    list_editable = ['orden']


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sala', 'frase', 'orden']
    list_editable = ['orden']
    prepopulated_fields = {'slug': ['nombre']}


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'area', 'rol', 'activo', 'orden']
    list_editable = ['activo', 'orden']
    list_filter = ['area', 'activo']
    filter_horizontal = ['disciplinas']


@admin.register(HorarioBase)
class HorarioBaseAdmin(admin.ModelAdmin):
    """La semana tipo. Los cambios se aplican a las clases que se creen desde ahora."""
    list_display = ['dia_semana', 'hora', 'sala', 'disciplina', 'instructor', 'nivel', 'activo']
    list_editable = ['disciplina', 'instructor', 'nivel', 'activo']
    list_filter = ['dia_semana', 'sala', 'disciplina', 'instructor']


@admin.action(description='Cancelar las clases seleccionadas (devuelve los créditos y avisa a las clientas)')
def cancelar_por_estudio(modeladmin, request, queryset):
    total_clases, total_reservas = 0, 0
    for clase in queryset.filter(cancelada=False, inicio__gt=timezone.now()):
        total_reservas += cancelar_clase_por_estudio(clase, 'Cancelada por el estudio')
        total_clases += 1
    modeladmin.message_user(
        request, f'Clases canceladas: {total_clases}. Reservas afectadas (con crédito devuelto y aviso): {total_reservas}.',
        messages.SUCCESS)


@admin.action(description='Crear las clases que falten de los próximos días (según el horario base)')
def crear_clases(modeladmin, request, queryset):
    creadas = generar_clases()
    modeladmin.message_user(request, f'Clases nuevas creadas: {creadas}.', messages.SUCCESS)


class ReservaEnLinea(admin.TabularInline):
    model = Reserva
    extra = 0
    fields = ['usuario', 'creada', 'cancelada', 'credito_devuelto']
    readonly_fields = fields
    can_delete = False


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ['inicio', 'sala', 'disciplina', 'instructor', 'nivel', 'reservas_confirmadas', 'cancelada']
    list_filter = ['sala', 'disciplina', 'instructor', 'cancelada']
    date_hierarchy = 'inicio'
    actions = [cancelar_por_estudio, crear_clases]
    inlines = [ReservaEnLinea]

    @admin.display(description='reservas')
    def reservas_confirmadas(self, clase):
        return clase.reservas_activas().count()


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['clase', 'usuario', 'creada', 'cancelada', 'credito_devuelto']
    list_filter = ['cancelada', 'clase__disciplina']
    search_fields = ['usuario__email', 'usuario__nombre', 'usuario__apellido']
    readonly_fields = ['usuario', 'clase', 'compra', 'creada', 'cancelada', 'cancelada_en', 'credito_devuelto']
