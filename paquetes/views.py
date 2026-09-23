from django.views.generic import TemplateView

from .models import paquetes_activos


class PaquetesView(TemplateView):
    template_name = 'paginas/paquetes.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = 'Paquetes'
        contexto['paquetes'] = paquetes_activos()
        return contexto
