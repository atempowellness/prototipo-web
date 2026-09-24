from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views import View
from django.views.generic import TemplateView

from clases.views import volver_a

from .models import TIPOS_PLURAL, Encuentro
from .servicios import (NoSePuedeInscribir, apertura_para, aperturas_avisadas, asegurar_encuentros_de_ejemplo,
                        cancelar_inscripcion,
                        compras_con_circle, estado_de_encuentro, inscribir, motivo_para_no_inscribirse,
                        pedir_o_quitar_aviso, proximos_encuentros, vence_antes_del_encuentro)


def _cuando(encuentro):
    local = timezone.localtime(encuentro.inicio)
    return f'{date_format(local, "l j \\d\\e F")} a las {local:%H:%M}'


class ComunidadView(TemplateView):
    template_name = 'comunidad/comunidad.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        asegurar_encuentros_de_ejemplo()
        tipo = self.request.GET.get('tipo', '')
        if tipo not in TIPOS_PLURAL:
            tipo = ''
        usuario = self.request.user
        if usuario.is_authenticated:
            # Se revisa aquí (y no solo en la campanita) para que el aviso aparezca en esta misma visita
            from notificaciones.avisos import revisar_aperturas
            revisar_aperturas(usuario)
            contexto['aperturas'] = aperturas_avisadas(usuario)
        contexto.update({
            'titulo': 'Comunidad',
            'tipos': list(TIPOS_PLURAL.items()),
            'tipo': tipo,
            'estados': [estado_de_encuentro(e, usuario) for e in proximos_encuentros(tipo)],
        })
        return contexto


class InscribirseView(LoginRequiredMixin, View):
    """GET: confirmación (página o ventana). POST: inscribe a la socia."""

    def get(self, request, pk):
        encuentro = get_object_or_404(Encuentro, pk=pk)
        compras = list(compras_con_circle(request.user, encuentro.fecha))
        contexto = {
            'titulo': 'Apuntarme',
            'encuentro': encuentro,
            'inicio': timezone.localtime(encuentro.inicio),
            'motivo': motivo_para_no_inscribirse(request.user, encuentro),
            'apertura': apertura_para(request.user, encuentro),
            'vence_antes': vence_antes_del_encuentro(request.user, encuentro),
            'compra': compras[0] if compras else None,
            'next': volver_a(request, reverse('comunidad')),
        }
        plantilla = 'comunidad/_confirmar_inscripcion.html' if request.GET.get('parcial') else 'comunidad/inscribirse.html'
        return render(request, plantilla, contexto)

    def post(self, request, pk):
        encuentro = get_object_or_404(Encuentro, pk=pk)
        destino = volver_a(request, reverse('comunidad'))
        try:
            inscripcion = inscribir(request.user, encuentro)
        except NoSePuedeInscribir as error:
            texto = str(error)
            if texto == 'SIN_ACCESO':
                texto = ('Los encuentros de Atempo Circle están incluidos en los paquetes desde Atempo 5, '
                         'vigentes el día del encuentro.')
            elif texto == 'AUN_NO':
                apertura = apertura_para(request.user, encuentro)
                texto = f'Tu inscripción a este encuentro se abre el {date_format(apertura, "l j \\d\\e F")}.'
            messages.error(request, texto)
            return redirect(destino)
        from notificaciones import avisos
        avisos.inscripcion_confirmada(inscripcion)
        messages.success(request, f'¡Listo! Te apuntaste a {encuentro.titulo}, el {_cuando(encuentro)}. ¡Te esperamos!')
        return redirect(destino)


class CancelarInscripcionView(LoginRequiredMixin, View):
    """GET: confirmación (página o ventana). POST: cancela la inscripción."""

    def get(self, request, pk):
        inscripcion = get_object_or_404(request.user.inscripciones.select_related('encuentro'), pk=pk, cancelada=False)
        contexto = {
            'titulo': 'Cancelar asistencia',
            'inscripcion': inscripcion,
            'encuentro': inscripcion.encuentro,
            'inicio': timezone.localtime(inscripcion.encuentro.inicio),
            'next': volver_a(request, reverse('cuenta')),
        }
        plantilla = ('comunidad/_confirmar_cancelacion.html' if request.GET.get('parcial')
                     else 'comunidad/cancelar.html')
        return render(request, plantilla, contexto)

    def post(self, request, pk):
        inscripcion = get_object_or_404(request.user.inscripciones, pk=pk, cancelada=False)
        destino = volver_a(request, reverse('cuenta'))
        if cancelar_inscripcion(inscripcion):
            messages.success(request, 'Cancelaste tu asistencia y liberaste tu cupo. ¡Gracias por avisar!')
        else:
            messages.error(request, 'Este encuentro ya empezó, así que no se puede cancelar.')
        return redirect(destino)


class RecordarmeView(LoginRequiredMixin, View):
    """Activa o quita el aviso en la campanita cuando se abra su inscripción."""

    def post(self, request, pk):
        encuentro = get_object_or_404(Encuentro, pk=pk, cancelado=False)
        destino = volver_a(request, reverse('comunidad'))
        apertura = apertura_para(request.user, encuentro)
        if apertura is None or apertura <= timezone.localdate():
            return redirect(destino)
        if pedir_o_quitar_aviso(request.user, encuentro):
            messages.success(request, f'Te avisaremos por correo y en la campanita el '
                                      f'{date_format(apertura, "l j \\d\\e F")}, cuando se abra tu inscripción.')
        else:
            messages.info(request, 'Listo, ya no te avisaremos de este encuentro.')
        return redirect(destino)
