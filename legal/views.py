import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import ReclamacionForm
from .models import DIAS_HABILES_PARA_RESPONDER, Reclamacion

ULTIMA_ACTUALIZACION = datetime.date(2026, 9, 24)


class PrivacidadView(TemplateView):
    template_name = 'legal/privacidad.html'
    extra_context = {'titulo': 'Política de privacidad', 'actualizado': ULTIMA_ACTUALIZACION}


class TerminosView(TemplateView):
    template_name = 'legal/terminos.html'
    extra_context = {'titulo': 'Términos y condiciones', 'actualizado': ULTIMA_ACTUALIZACION}


class LibroView(FormView):
    """Libro de Reclamaciones virtual: formulario y, al enviarlo, la constancia (simulada)."""
    template_name = 'legal/libro.html'
    form_class = ReclamacionForm
    extra_context = {'titulo': 'Libro de reclamaciones', 'dias_habiles': DIAS_HABILES_PARA_RESPONDER}

    def get_initial(self):
        # Con sesión iniciada, los datos de la persona se llenan solos
        usuario = self.request.user
        if not usuario.is_authenticated:
            return {}
        return {'nombre': usuario.get_full_name(), 'dni': usuario.dni or '', 'email': usuario.email,
                'telefono': usuario.celular or ''}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # Después de enviar, se muestra la constancia de la hoja recién presentada (guardada en la sesión)
        if self.request.GET.get('enviada'):
            pk = self.request.session.get('ultima_reclamacion')
            contexto['reclamacion'] = Reclamacion.objects.filter(pk=pk).first() if pk else None
        return contexto

    def form_valid(self, form):
        reclamacion = form.save(commit=False)
        if self.request.user.is_authenticated:
            reclamacion.usuario = self.request.user
        reclamacion.save()
        if reclamacion.usuario:
            from notificaciones import avisos
            avisos.reclamacion_recibida(reclamacion)
        # Redirigir evita que, al recargar la página, se envíe dos veces
        self.request.session['ultima_reclamacion'] = reclamacion.pk
        return redirect(reverse('reclamaciones') + '?enviada=1')


class QuitarReclamacionView(LoginRequiredMixin, View):
    """
    Quita una hoja ya respondida de Mi cuenta. No se borra: el estudio la sigue
    viendo en el panel, porque la norma obliga a conservarla.
    """
    def _hoja(self, request, pk):
        return get_object_or_404(request.user.reclamaciones, pk=pk, estado=Reclamacion.RESPONDIDA,
                                 quitada_por_clienta=False)

    def get(self, request, pk):
        contexto = {'titulo': 'Quitar de Mi cuenta', 'reclamacion': self._hoja(request, pk)}
        plantilla = 'legal/_confirmar_quitar.html' if request.GET.get('parcial') else 'legal/quitar.html'
        return render(request, plantilla, contexto)

    def post(self, request, pk):
        hoja = self._hoja(request, pk)
        hoja.quitada_por_clienta = True
        hoja.save(update_fields=['quitada_por_clienta'])
        messages.success(request, f'Quitamos la hoja N.° {hoja.numero} de tu cuenta.')
        return redirect(reverse('cuenta'))
