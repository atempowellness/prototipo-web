from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Reclamacion


@admin.register(Reclamacion)
class ReclamacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'creada', 'tipo', 'nombre', 'servicio', 'estado_con_color']
    list_filter = ['estado', 'tipo', 'servicio', 'quitada_por_clienta']
    search_fields = ['numero', 'nombre', 'dni', 'email']
    date_hierarchy = 'creada'
    readonly_fields = ['numero', 'creada', 'usuario', 'nombre', 'dni', 'domicilio', 'telefono', 'email',
                       'servicio', 'monto', 'descripcion_servicio', 'tipo', 'detalle', 'pedido', 'respondida_en',
                       'quitada_por_clienta']
    fieldsets = [
        ('Hoja de reclamación', {'fields': ['numero', 'creada', 'tipo', 'usuario', 'quitada_por_clienta']}),
        ('Quien reclama', {'fields': ['nombre', 'dni', 'domicilio', 'telefono', 'email']}),
        ('Servicio', {'fields': ['servicio', 'monto', 'descripcion_servicio']}),
        ('Detalle', {'fields': ['detalle', 'pedido']}),
        ('Respuesta del estudio', {'fields': ['estado', 'respuesta', 'respondida_en'],
                                   'description': 'Al marcarla como "Respondida" con una respuesta, '
                                                  'la clienta recibe un aviso en la campanita (si tiene cuenta).'}),
    ]

    @admin.display(description='estado', ordering='estado')
    def estado_con_color(self, reclamacion):
        """Verde si está respondida, rojo si está pendiente (estilos en static/css/panel.css)."""
        return format_html('<span class="estado estado-{}">{}</span>',
                           reclamacion.estado, reclamacion.get_estado_display())

    def has_add_permission(self, request):
        return False   # las hojas se presentan desde la web

    def save_model(self, request, reclamacion, form, change):
        recien_respondida = (reclamacion.estado == Reclamacion.RESPONDIDA and reclamacion.respuesta
                             and not reclamacion.respondida_en)
        if recien_respondida:
            reclamacion.respondida_en = timezone.now()
        super().save_model(request, reclamacion, form, change)
        if recien_respondida and reclamacion.usuario:
            from notificaciones import avisos
            avisos.reclamacion_respondida(reclamacion)
