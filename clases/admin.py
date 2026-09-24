from django.contrib import admin, messages
from django.utils import timezone

from .models import Clase, Disciplina, HorarioBase, ListaEspera, Profesional, Reserva, Sala
from core.admin import EliminarSoloPruebasMixin

from .lista_espera import procesar_lista, revisar_listas_de_espera
from .servicios import cancelar_clase_por_estudio, cancelar_reserva, generar_clases


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


@admin.action(description='Cancelar las clases seleccionadas (devuelve los puntos y avisa a las clientas)')
def cancelar_por_estudio(modeladmin, request, queryset):
    total_clases, total_reservas = 0, 0
    for clase in queryset.filter(cancelada=False, inicio__gt=timezone.now()):
        total_reservas += cancelar_clase_por_estudio(clase, 'Cancelada por el estudio')
        total_clases += 1
    modeladmin.message_user(
        request, f'Clases canceladas: {total_clases}. Reservas afectadas (con punto devuelto y aviso): {total_reservas}.',
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


class ListaEsperaEnLinea(admin.TabularInline):
    model = ListaEspera
    extra = 0
    fields = ['usuario', 'creada', 'estado', 'oferta_vence']
    readonly_fields = fields
    can_delete = False
    verbose_name_plural = 'lista de espera'


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ['inicio', 'sala', 'disciplina', 'instructor', 'nivel', 'reservas_confirmadas', 'cancelada']
    list_filter = ['sala', 'disciplina', 'instructor', 'cancelada']
    date_hierarchy = 'inicio'
    actions = [cancelar_por_estudio, crear_clases]
    inlines = [ReservaEnLinea, ListaEsperaEnLinea]

    @admin.display(description='reservas')
    def reservas_confirmadas(self, clase):
        return clase.reservas_activas().count()


@admin.action(description='Cancelar las reservas seleccionadas (devuelve el punto y avisa a la clienta)')
def cancelar_reservas_por_estudio(modeladmin, request, queryset):
    total = 0
    for reserva in queryset.filter(cancelada=False).select_related('clase', 'usuario'):
        cancelar_reserva(reserva, por_el_estudio=True)
        total += 1
    texto = '1 reserva cancelada' if total == 1 else f'{total} reservas canceladas'
    modeladmin.message_user(request, f'{texto}, con el punto devuelto y aviso a la clienta.', messages.SUCCESS)


@admin.register(Reserva)
class ReservaAdmin(EliminarSoloPruebasMixin, admin.ModelAdmin):
    actions = [cancelar_reservas_por_estudio]
    list_display = ['clase', 'usuario', 'creada', 'cancelada', 'credito_devuelto']
    list_filter = ['cancelada', 'clase__disciplina']
    search_fields = ['usuario__email', 'usuario__nombre', 'usuario__apellido']
    readonly_fields = ['usuario', 'clase', 'compra', 'creada', 'cancelada', 'cancelada_en', 'credito_devuelto']


@admin.action(description='Adelantar el reloj: vencer ahora el plazo de los cupos ofrecidos (solo para pruebas)')
def vencer_ofertas(modeladmin, request, queryset):
    ofrecidos = list(queryset.filter(estado=ListaEspera.OFRECIDO).select_related('clase'))
    for puesto in ofrecidos:
        ListaEspera.objects.filter(pk=puesto.pk).update(oferta_vence=timezone.now())
        procesar_lista(puesto.clase)   # vence la oferta y pasa el cupo a la siguiente
    texto = '1 plazo vencido' if len(ofrecidos) == 1 else f'{len(ofrecidos)} plazos vencidos'
    modeladmin.message_user(request, f'{texto}: el cupo pasó a la siguiente persona de la lista (si había).',
                            messages.SUCCESS)


@admin.register(ListaEspera)
class ListaEsperaAdmin(admin.ModelAdmin):
    actions = [vencer_ofertas]
    list_display = ['clase', 'usuario', 'creada', 'estado', 'oferta_vence']
    list_filter = ['estado', 'clase__disciplina']
    search_fields = ['usuario__email', 'usuario__nombre', 'usuario__apellido']
    readonly_fields = ['usuario', 'clase', 'creada', 'estado', 'oferta_desde', 'oferta_vence', 'reserva']

    def has_add_permission(self, request):
        return False   # las socias se anotan desde la web

    def changelist_view(self, request, extra_context=None):
        revisar_listas_de_espera()   # plazos al día antes de mostrar la lista
        return super().changelist_view(request, extra_context)
