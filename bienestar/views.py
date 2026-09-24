import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views import View
from django.views.generic import TemplateView

from clases.models import HORAS_PARA_CANCELAR, Profesional
from clases.views import etiqueta_dia, volver_a
from paquetes.models import Paquete

from .forms import FichaNutricionForm
from .models import MASAJES, NUTRICION, SERVICIOS, TipoSesion
from .servicios import (CAMPO_COSTO, CAMPO_INCLUIDAS, NoSePuedeAgendar, agendar, cancelar_cita, dias_disponibles,
                        horas_libres, plan_de_pago, profesionales_de, sesiones_incluidas_disponibles)

TEXTOS = {
    NUTRICION: {
        'titulo': 'Nutrición',
        'descripcion': 'Evaluación de tus hábitos y un plan de alimentación realista, pensado para acompañar '
                       'tu entrenamiento y los cambios de esta etapa.',
        'imagen': 'Asesoría nutricional',
    },
    MASAJES: {
        'titulo': 'Masajes',
        'descripcion': 'Descarga muscular para recuperarte después de entrenar, o una sesión relajante para '
                       'desconectar del ritmo de la semana.',
        'imagen': 'Sala de masajes',
    },
}


def servicio_valido(servicio):
    if servicio not in dict(SERVICIOS):
        raise Http404
    return servicio


def condiciones_del_servicio(servicio):
    """Textos de qué paquetes lo incluyen y cuánto cuesta la sesión adicional (salen del panel)."""
    total, _ = CAMPO_INCLUIDAS[servicio]
    incluido_desde = Paquete.objects.filter(activo=True, **{f'{total}__gt': 0}).order_by('creditos').first()
    con_adicional = Paquete.objects.filter(activo=True, **{f'{CAMPO_COSTO[servicio]}__isnull': False}) \
        .order_by('creditos').first()
    return {
        'incluido_desde': incluido_desde.nombre if incluido_desde else '',
        'costo_adicional': getattr(con_adicional, CAMPO_COSTO[servicio]) if con_adicional else None,
        'adicional_desde': con_adicional.nombre if con_adicional else '',
    }


def resumen(servicio, usuario):
    datos = {'clave': servicio, **TEXTOS[servicio], **condiciones_del_servicio(servicio),
             'profesionales': profesionales_de(servicio)}
    if usuario.is_authenticated:
        datos['incluidas'] = sesiones_incluidas_disponibles(usuario, servicio)
    return datos


class BienestarView(TemplateView):
    """Presentación de los dos servicios."""
    template_name = 'bienestar/bienestar.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = 'Bienestar: nutrición y masajes'
        contexto['servicios'] = [resumen(s, self.request.user) for s in (NUTRICION, MASAJES)]
        return contexto


class ServicioView(TemplateView):
    """Página de un servicio, con la agenda para elegir tipo, profesional, día y hora."""
    template_name = 'bienestar/servicio.html'

    def get_context_data(self, servicio, **kwargs):
        contexto = super().get_context_data(**kwargs)
        servicio = servicio_valido(servicio)
        tipos = list(TipoSesion.objects.filter(servicio=servicio))
        profesionales = list(profesionales_de(servicio))
        get = self.request.GET

        tipo = next((t for t in tipos if str(t.pk) == get.get('tipo')), tipos[0] if tipos else None)
        profesional = next((p for p in profesionales if str(p.pk) == get.get('profesional')), None)
        dias = dias_disponibles()
        try:
            dia = datetime.date.fromisoformat(get.get('dia', ''))
        except ValueError:
            dia = dias[0]
        if dia not in dias:
            dia = dias[0]

        libres = horas_libres(servicio, tipo, dia, profesional, self.request.user) if tipo else []
        contexto.update({
            'titulo': TEXTOS[servicio]['titulo'],
            'servicio': resumen(servicio, self.request.user),
            'tipos': tipos, 'tipo': tipo,
            'profesionales': profesionales, 'profesional': profesional,
            'varias_profesionales': len(profesionales) > 1,
            'dias': [(d, etiqueta_dia(d)) for d in dias], 'dia': dia,
            'dia_largo': date_format(dia, 'l j \\d\\e F'),
            'libres': [{'inicio': timezone.localtime(i), 'profesional': p} for i, p in libres],
        })
        return contexto


def leer_inicio(texto):
    try:
        momento = datetime.datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        raise Http404
    return timezone.make_aware(momento) if timezone.is_naive(momento) else momento


class AgendarView(LoginRequiredMixin, View):
    """GET: confirmación (ventana o página). POST: agenda la cita."""

    def datos(self, request, servicio):
        servicio = servicio_valido(servicio)
        fuente = request.POST if request.method == 'POST' else request.GET
        tipo = get_object_or_404(TipoSesion, pk=fuente.get('tipo'), servicio=servicio)
        profesional = get_object_or_404(Profesional, pk=fuente.get('profesional'), area=servicio, activo=True)
        inicio = leer_inicio(fuente.get('inicio'))
        return servicio, tipo, profesional, inicio

    def contexto(self, request, servicio, tipo, profesional, inicio, ficha=None):
        local = timezone.localtime(inicio)
        return {
            'titulo': f'Agendar {TEXTOS[servicio]["titulo"].lower()}',
            'servicio': servicio, 'tipo': tipo, 'profesional': profesional,
            'inicio': local, 'inicio_valor': local.strftime('%Y-%m-%dT%H:%M'),
            'plan': plan_de_pago(request.user, servicio, local.date()),
            'ficha': ficha if ficha is not None else (FichaNutricionForm() if tipo.pide_ficha else None),
            'horas_para_cancelar': HORAS_PARA_CANCELAR,
            'sin_devolucion': inicio - timezone.now() < datetime.timedelta(hours=HORAS_PARA_CANCELAR),
            'next': volver_a(request, reverse('bienestar_servicio', args=[servicio])),
        }

    def get(self, request, servicio):
        servicio, tipo, profesional, inicio = self.datos(request, servicio)
        plantilla = 'bienestar/_confirmar_cita.html' if request.GET.get('parcial') else 'bienestar/agendar.html'
        return render(request, plantilla, self.contexto(request, servicio, tipo, profesional, inicio))

    def post(self, request, servicio):
        servicio, tipo, profesional, inicio = self.datos(request, servicio)
        destino = volver_a(request, reverse('bienestar_servicio', args=[servicio]))
        ficha_datos = None
        if tipo.pide_ficha:
            ficha = FichaNutricionForm(request.POST)
            if not ficha.is_valid():
                # Se muestra de nuevo, en página propia, con los errores debajo de cada campo
                return render(request, 'bienestar/agendar.html',
                              self.contexto(request, servicio, tipo, profesional, inicio, ficha))
            d = ficha.cleaned_data
            ficha_datos = {'objetivo': d['objetivo'], 'alergias': d['alergias'], 'condiciones': d['condiciones'],
                           'consentimiento_salud': timezone.now()}
        try:
            cita = agendar(request.user, profesional, tipo, inicio, ficha_datos)
        except NoSePuedeAgendar as error:
            texto = str(error)
            if texto == 'SIN_SESIONES':
                texto = 'No tienes sesiones ni créditos disponibles para esta cita. Revisa los paquetes.'
            messages.error(request, texto)
            return redirect(destino)

        from notificaciones import avisos
        avisos.cita_confirmada(cita)
        local = timezone.localtime(cita.inicio)
        messages.success(request, f'¡Listo! Agendaste {tipo.nombre.lower()} con {profesional.nombre} el '
                                  f'{date_format(local, "l j \\d\\e F")} a las {local:%H:%M}.')
        return redirect(destino)


class CancelarCitaView(LoginRequiredMixin, View):
    def get(self, request, pk):
        cita = get_object_or_404(request.user.citas.select_related('tipo', 'profesional'), pk=pk, cancelada=False)
        contexto = {
            'titulo': 'Cancelar cita', 'cita': cita, 'inicio': timezone.localtime(cita.inicio),
            'se_devuelve': cita.se_devuelve_si_cancela, 'horas_para_cancelar': HORAS_PARA_CANCELAR,
            'next': volver_a(request, reverse('cuenta')),
        }
        plantilla = 'bienestar/_confirmar_cancelacion.html' if request.GET.get('parcial') else 'bienestar/cancelar.html'
        return render(request, plantilla, contexto)

    def post(self, request, pk):
        cita = get_object_or_404(request.user.citas, pk=pk, cancelada=False)
        destino = volver_a(request, reverse('cuenta'))
        if cita.empezo:
            messages.error(request, 'Esta cita ya empezó, así que no se puede cancelar.')
            return redirect(destino)
        if cancelar_cita(cita):
            que = 'la sesión' if cita.forma == 'incluida' else 'los créditos'
            messages.success(request, f'Cancelaste tu cita. Te devolvimos {que}.')
        else:
            messages.info(request, f'Cancelaste tu cita. Como faltaban menos de {HORAS_PARA_CANCELAR} horas, '
                                   'no se devuelve la sesión ni los créditos.')
        return redirect(destino)
