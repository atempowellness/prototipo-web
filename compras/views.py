from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView

from notificaciones import avisos
from paquetes.models import Paquete, paquete_founding, paquetes_activos, puede_comprar_founding

from .forms import PagoForm
from .models import compras_pagadas, creditos_disponibles, registrar_compra
from .referidas import CREDITOS_MINIMOS, activara_beneficio, aplicar_beneficio, aviso_paquete_menor


class ComprarView(LoginRequiredMixin, FormView):
    """Página de pago (simulado) de un paquete."""
    template_name = 'compras/comprar.html'
    form_class = PagoForm

    def dispatch(self, request, *args, **kwargs):
        self.paquete = get_object_or_404(Paquete.objects.filter(activo=True), slug=kwargs['slug'])
        if self.paquete.es_founding and request.user.is_authenticated:
            # Founding Members: solo mientras queden ventas y como primera compra
            if paquete_founding() is None:
                messages.info(request, 'La preventa Founding Members ya se agotó. ¡Gracias por tu interés!')
                return redirect('paquetes')
            if not puede_comprar_founding(request.user):
                messages.info(request, 'El paquete Founding Members es solo para la primera compra.')
                return redirect('paquetes')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(usuario=self.request.user, paquete=self.paquete)
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = f'Comprar {self.paquete.nombre}'
        contexto['paquete'] = self.paquete
        # Si ya puso un código al registrarse y esta compra lo activa, se le avisa
        if activara_beneficio(self.request.user, self.paquete):
            contexto['beneficio_referida'] = self.request.user.referida_por
        # Si compra Atempo 1, se le recuerda que el punto extra se activa desde Atempo 5
        contexto['aviso_paquete_menor'] = aviso_paquete_menor(self.request.user, self.paquete)
        contexto['paquete_minimo'] = paquetes_activos().filter(creditos__gte=CREDITOS_MINIMOS).first()
        # Si todavía puede ser Founding Member, se le avisa antes de gastar su primera compra en otro paquete
        founding = paquete_founding()
        if founding and not self.paquete.es_founding and puede_comprar_founding(self.request.user):
            contexto['founding'] = founding
        return contexto

    def form_valid(self, form):
        datos = form.cleaned_data
        usuario = self.request.user
        if datos.get('codigo_referida'):
            usuario.referida_por = datos['codigo_referida']
            usuario.save(update_fields=['referida_por'])

        compra = registrar_compra(usuario, self.paquete, datos['metodo'], datos['detalle_pago'])
        avisos.creditos_activados(compra)

        resultado = aplicar_beneficio(compra)
        if resultado:
            amiga = resultado['invitadora'].nombre
            texto = f'¡Recibiste 1 punto de regalo por venir invitada por {amiga}!'
            if resultado['invitadora_recibe']:
                texto += f' {amiga} también recibe el suyo.'
            messages.success(self.request, texto)
        return redirect(reverse('compra', args=[compra.pk]) + '?nueva=1')


class CompraView(LoginRequiredMixin, DetailView):
    """Confirmación de la compra y boleta simulada. Cada clienta solo ve sus compras."""
    template_name = 'compras/compra.html'
    context_object_name = 'compra'

    def get_queryset(self):
        return compras_pagadas(self.request.user)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = f'Compra {self.object.nombre_paquete}'
        contexto['nueva'] = self.request.GET.get('nueva') == '1'
        contexto['creditos_totales'] = creditos_disponibles(self.request.user)
        return contexto
