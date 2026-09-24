from django.contrib import admin

from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['creada', 'usuario', 'tipo', 'texto', 'leida']
    list_filter = ['tipo', 'leida']
    search_fields = ['usuario__email', 'usuario__nombre', 'texto']
