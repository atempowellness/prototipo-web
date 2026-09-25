from django.contrib import admin

from .models import Paquete


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'creditos', 'vigencia_meses', 'precio', 'etiqueta_destacado', 'activo', 'orden']
    list_editable = ['precio', 'activo', 'orden']
    prepopulated_fields = {'slug': ['nombre']}
    fieldsets = [
        (None, {'fields': ['nombre', 'slug', 'creditos', 'vigencia_meses', 'precio']}),
        ('Beneficios incluidos', {'fields': [
            'sesiones_nutricion', 'sesiones_masaje', 'incluye_circle', 'dias_inscripcion_circle',
            'costo_nutricion_adicional', 'costo_masaje_adicional',
        ]}),
        ('Cómo se muestra en la web', {'fields': ['frase', 'etiqueta_destacado', 'orden', 'activo']}),
    ]
    readonly_fields = ['ventas_founding']
    SECCION_FOUNDING = ('Preventa Founding Members', {
        'fields': ['ventas_founding', 'ventas_maximas', 'precio_referencia', 'es_founding'],
        'description': 'Se vende únicamente como primera compra y desaparece de la web al llegar al máximo de '
                       'ventas. El precio de referencia es el precio normal, que se muestra tachado.'})

    def get_fieldsets(self, request, obj=None):
        # La sección de preventa va primero (y abierta) solo en el paquete Founding Members
        if obj is not None and obj.es_founding:
            return [self.SECCION_FOUNDING, *self.fieldsets]
        return self.fieldsets

    def get_list_display(self, request):
        return [*self.list_display, 'ventas_founding']

    @admin.display(description='preventa: vendidos')
    def ventas_founding(self, paquete):
        if not paquete.es_founding:
            return '—'
        return f'{paquete.vendidos} de {paquete.ventas_maximas or 0} (quedan {paquete.quedan})'
