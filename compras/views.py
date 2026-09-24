from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect

from django.urls import reverse
from django.views.generic import DetailView, FormView

from paquetes.models import paquetes_activos

from .forms import PagoForm
from .models import creditos_disponibles, registrar_compra


class ComprarView(LoginRequiredMixin, FormView):
    """Página de pago (simulado) de un paquete."""
    template_name = 'compras/comprar.html'
    form_class = PagoForm

    def dispatch(self, request, *args, **kwargs):
        self.paquete = get_object_or_404(paquetes_activos(), slug=kwargs['slug'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = f'Comprar {self.paquete.nombre}'
        contexto['paquete'] = self.paquete
        return contexto

    def form_valid(self, form):
        datos = form.cleaned_data
        compra = registrar_compra(self.request.user, self.paquete, datos['metodo'], datos['detalle_pago'])
        return redirect(reverse('compra', args=[compra.pk]) + '?nueva=1')


class CompraView(LoginRequiredMixin, DetailView):
    """Confirmación de la compra y boleta simulada. Cada clienta solo ve sus compras."""
    template_name = 'compras/compra.html'
    context_object_name = 'compra'

    def get_queryset(self):
        return self.request.user.compras.all()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = f'Compra {self.object.nombre_paquete}'
        contexto['nueva'] = self.request.GET.get('nueva') == '1'
        contexto['creditos_totales'] = creditos_disponibles(self.request.user)
        return contexto
