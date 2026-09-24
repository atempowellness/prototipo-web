"""
Ajustes del panel de administración que aplican a todas las secciones.

La traducción de Django para "eliminar seleccionados" siempre usa el singular
("eliminar el usuarios seleccionado", "Eliminado/s 2 usuarios"). Esta acción
hace exactamente lo mismo que la original, pero con frases que cambian entre
singular y plural según cuántos registros se seleccionen.
La pantalla de confirmación está en templates/admin/delete_selected_confirmation.html.
"""
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse


def nombre_segun_cantidad(opts, cantidad):
    return opts.verbose_name if cantidad == 1 else opts.verbose_name_plural


@admin.action(permissions=['delete'], description='Eliminar %(verbose_name_plural)s seleccionados')
def eliminar_seleccionados(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    objetos, conteo, permisos_faltantes, protegidos = modeladmin.get_deleted_objects(queryset, request)

    # Ya confirmó: se elimina y se vuelve a la lista
    if request.POST.get('post') and not protegidos:
        if permisos_faltantes:
            raise PermissionDenied
        cantidad = len(queryset)
        if cantidad:
            modeladmin.log_deletions(request, queryset)
            modeladmin.delete_queryset(request, queryset)
            if cantidad == 1:
                texto = f'Se eliminó 1 {opts.verbose_name} correctamente.'
            else:
                texto = f'Se eliminaron {cantidad} {opts.verbose_name_plural} correctamente.'
            modeladmin.message_user(request, texto, messages.SUCCESS)
        return None

    # Pantalla de confirmación
    cantidad = len(queryset)
    nombre = nombre_segun_cantidad(opts, cantidad)
    contexto = {
        **modeladmin.admin_site.each_context(request),
        'title': f'No se puede eliminar' if (permisos_faltantes or protegidos) else 'Confirmar eliminación',
        'subtitle': None,
        'cantidad': cantidad,
        'objects_name': str(nombre),
        'deletable_objects': [objetos],
        'model_count': dict(conteo).items(),
        'queryset': queryset,
        'perms_lacking': permisos_faltantes,
        'protected': protegidos,
        'opts': opts,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'media': modeladmin.media,
    }
    request.current_app = modeladmin.admin_site.name
    return TemplateResponse(request, 'admin/delete_selected_confirmation.html', contexto)


class EliminarSoloPruebasMixin:
    """
    Para reservas de clases y citas: "Eliminar" borra el registro sin devolver puntos ni
    avisar a la clienta, así que se rotula como opción para pruebas. Para anular algo de
    verdad se usa la acción "Cancelar…" de cada sección.
    """
    def get_actions(self, request):
        acciones = super().get_actions(request)
        if 'delete_selected' in acciones:
            funcion, nombre, _ = acciones['delete_selected']
            acciones['delete_selected'] = (funcion, nombre,
                                           'Eliminar sin devolver ni avisar (solo para pruebas)')
        return acciones


# Reemplaza la acción original en todas las secciones del panel
admin.site.disable_action('delete_selected')
admin.site.add_action(eliminar_seleccionados, 'delete_selected')
