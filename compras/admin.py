from django.contrib import admin

from .models import Compra


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'tipo', 'nombre_paquete', 'precio_pagado', 'metodo',
                    'creditos', 'creditos_usados', 'vence']
    list_filter = ['tipo', 'metodo', 'nombre_paquete', 'fecha']
    search_fields = ['usuario__email', 'usuario__nombre', 'usuario__apellido', 'usuario__dni', 'numero_operacion']
    date_hierarchy = 'fecha'
    readonly_fields = ['tipo', 'referida', 'usuario', 'paquete', 'fecha', 'nombre_paquete', 'creditos', 'precio_pagado',
                       'sesiones_nutricion', 'sesiones_masaje', 'incluye_circle',
                       'metodo', 'detalle_pago', 'numero_operacion']
    fieldsets = [
        ('Compra', {'fields': ['tipo', 'usuario', 'paquete', 'referida', 'fecha', 'vence',
                               'nombre_paquete', 'precio_pagado']}),
        ('Créditos y beneficios', {'fields': [
            'creditos', 'creditos_usados', 'sesiones_nutricion', 'nutricion_usada',
            'sesiones_masaje', 'masaje_usado', 'incluye_circle']}),
        ('Pago (simulado)', {'fields': ['metodo', 'detalle_pago', 'numero_operacion']}),
    ]

    def has_add_permission(self, request):
        # Las compras se hacen desde la web. Registrar pagos en recepción queda pendiente.
        return False
