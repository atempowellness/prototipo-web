from django.views.generic import TemplateView

from .models import paquete_founding, paquetes_activos, puede_comprar_founding


class PaquetesView(TemplateView):
    template_name = 'paginas/paquetes.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = 'Paquetes'
        contexto['paquetes'] = paquetes_activos()
        # Preventa Founding Members: aparte, mientras queden ventas
        contexto['founding'] = paquete_founding()
        contexto['puede_founding'] = puede_comprar_founding(self.request.user)
        return contexto
