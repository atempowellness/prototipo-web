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
            'sesiones_nutricion', 'sesiones_masaje', 'incluye_circle',
            'costo_nutricion_adicional', 'costo_masaje_adicional',
        ]}),
        ('Cómo se muestra en la web', {'fields': ['frase', 'etiqueta_destacado', 'orden', 'activo']}),
    ]
