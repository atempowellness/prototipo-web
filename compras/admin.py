from django.contrib import admin

from .models import Compra


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'nombre_paquete', 'precio_pagado', 'metodo',
                    'creditos', 'creditos_usados', 'vence']
    list_filter = ['metodo', 'nombre_paquete', 'fecha']
    search_fields = ['usuario__email', 'usuario__nombre', 'usuario__apellido', 'usuario__dni', 'numero_operacion']
    date_hierarchy = 'fecha'
    readonly_fields = ['usuario', 'paquete', 'fecha', 'nombre_paquete', 'creditos', 'precio_pagado',
                       'sesiones_nutricion', 'sesiones_masaje', 'incluye_circle',
                       'metodo', 'detalle_pago', 'numero_operacion']
    fieldsets = [
        ('Compra', {'fields': ['usuario', 'paquete', 'fecha', 'vence', 'nombre_paquete', 'precio_pagado']}),
        ('Créditos y beneficios', {'fields': [
            'creditos', 'creditos_usados', 'sesiones_nutricion', 'nutricion_usada',
            'sesiones_masaje', 'masaje_usado', 'incluye_circle']}),
        ('Pago (simulado)', {'fields': ['metodo', 'detalle_pago', 'numero_operacion']}),
    ]

    def has_add_permission(self, request):
        # Las compras se hacen desde la web. Registrar pagos en recepción queda pendiente.
        return False
