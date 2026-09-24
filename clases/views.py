import datetime
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from compras.models import compra_para_usar

from .models import DIAS_PARA_RESERVAR, HORAS_PARA_CANCELAR, NIVELES, Clase, Disciplina, Reserva
from .servicios import (FRANJAS, NoSePuedeReservar, cancelar_reserva, clases_del_dia, dias_disponibles,
                        generar_clases, motivo_para_no_reservar, reserva_activa, reservar)

CUPOS_POCOS = 3   # desde cuántos cupos se muestra "Quedan X cupos" (el aforo no se muestra)


def simulando(request):
    """¿Está activado el modo "simular ocupación"? (apagado por defecto)."""
    return request.session.get('simular_ocupacion', False)


def volver_a(request, por_defecto):
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return destino
    return por_defecto


def etiqueta_dia(dia):
    hoy = timezone.localdate()
    if dia == hoy:
        return 'Hoy'
    if dia == hoy + datetime.timedelta(days=1):
        return 'Mañana'
    return date_format(dia, 'D d').capitalize()   # "Jue 01" (días con dos dígitos)


def asegurar_clases():
    """Crea las clases que falten para los próximos días (solo si falta el último día)."""
    ultimo = timezone.localdate() + datetime.timedelta(days=DIAS_PARA_RESERVAR)
    zona = timezone.get_current_timezone()
    desde = timezone.make_aware(datetime.datetime.combine(ultimo, datetime.time.min), zona)
    if not Clase.objects.filter(inicio__gte=desde, inicio__lt=desde + datetime.timedelta(days=1)).exists():
        generar_clases()


def estado_de_clase(clase, usuario, simular):
    """Todo lo que la tarjeta de una clase necesita mostrar."""
    cupos = clase.cupos(simular)
    return {
        'clase': clase,
        'mi_reserva': reserva_activa(usuario, clase),
        'llena': cupos <= 0,
        'pocos_cupos': 0 < cupos <= CUPOS_POCOS,
        'cupos': cupos,
    }


class HorariosView(TemplateView):
    template_name = 'clases/horarios.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        asegurar_clases()
        dias = dias_disponibles()
        try:
            dia = datetime.date.fromisoformat(self.request.GET.get('dia', ''))
        except ValueError:
            dia = dias[0]
        if dia not in dias:
            dia = dias[0]
        disciplina = self.request.GET.get('disciplina', '')
        franja = self.request.GET.get('franja', '')
        simular = simulando(self.request)
        usuario = self.request.user

        estados = [estado_de_clase(c, usuario, simular) for c in clases_del_dia(dia, disciplina, franja)]
        por_hora = [(hora, list(grupo)) for hora, grupo in
                    groupby(estados, key=lambda e: timezone.localtime(e['clase'].inicio).strftime('%H:%M'))]

        contexto.update({
            'titulo': 'Clases',
            'dias': [(d, etiqueta_dia(d)) for d in dias],
            'dia': dia,
            'dia_largo': date_format(dia, 'l j \\d\\e F'),
            'disciplinas': Disciplina.objects.all(),
            'disciplina': disciplina,
            'franjas': [(clave, nombre) for clave, nombre, _, _ in FRANJAS],
            'franja': franja,
            'niveles': NIVELES,
            'por_hora': por_hora,
            'simular': simular,
            'dias_para_reservar': DIAS_PARA_RESERVAR,
        })
        return contexto


class ReservarView(LoginRequiredMixin, View):
    """GET: confirmación (página o ventana). POST: hace la reserva."""

    def get(self, request, pk):
        clase = get_object_or_404(Clase.objects.select_related('sala', 'disciplina', 'instructor'), pk=pk)
        motivo = motivo_para_no_reservar(request.user, clase, simulando(request))
        contexto = {
            'titulo': 'Reservar clase',
            'clase': clase,
            'inicio': timezone.localtime(clase.inicio),
            'motivo': motivo,
            'compra': compra_para_usar(request.user, clase.fecha),
            'horas_para_cancelar': HORAS_PARA_CANCELAR,
            # Si empieza en menos de 12 horas, se advierte ANTES de confirmar que no hay devolución
            'sin_devolucion': clase.inicio - timezone.now() < datetime.timedelta(hours=HORAS_PARA_CANCELAR),
            'next': volver_a(request, reverse('horarios') + f'?dia={clase.fecha.isoformat()}'),
        }
        plantilla = 'clases/_confirmar_reserva.html' if request.GET.get('parcial') else 'clases/reservar.html'
        return render(request, plantilla, contexto)

    def post(self, request, pk):
        clase = get_object_or_404(Clase, pk=pk)
        destino = volver_a(request, reverse('horarios') + f'?dia={clase.fecha.isoformat()}')
        try:
            reserva = reservar(request.user, clase, simulando(request))
        except NoSePuedeReservar as error:
            texto = str(error)
            if texto == 'SIN_CREDITOS':
                texto = 'Necesitas un punto vigente para esa fecha. Puedes comprar un paquete en Paquetes.'
            messages.error(request, texto)
            return redirect(destino)
        from notificaciones import avisos
        avisos.reserva_confirmada(reserva)

        inicio = timezone.localtime(clase.inicio)
        origen = reserva.compra.origen if reserva.compra else 'de tus puntos'
        messages.success(request, f'¡Listo! Reservaste {clase.disciplina.nombre} el '
                                  f'{date_format(inicio, "l j \\d\\e F")} a las {inicio:%H:%M} en {clase.sala.nombre}. '
                                  f'Se usó 1 punto {origen}.')
        return redirect(destino)


class CancelarView(LoginRequiredMixin, View):
    """GET: confirmación (página o ventana). POST: cancela la reserva."""

    def get(self, request, pk):
        reserva = get_object_or_404(request.user.reservas.select_related('clase__sala', 'clase__disciplina'),
                                    pk=pk, cancelada=False)
        contexto = {
            'titulo': 'Cancelar reserva',
            'reserva': reserva,
            'clase': reserva.clase,
            'inicio': timezone.localtime(reserva.clase.inicio),
            'se_devuelve': reserva.se_devuelve_si_cancela,
            'horas_para_cancelar': HORAS_PARA_CANCELAR,
            'next': volver_a(request, reverse('cuenta')),
        }
        plantilla = 'clases/_confirmar_cancelacion.html' if request.GET.get('parcial') else 'clases/cancelar.html'
        return render(request, plantilla, contexto)

    def post(self, request, pk):
        reserva = get_object_or_404(request.user.reservas, pk=pk, cancelada=False)
        destino = volver_a(request, reverse('cuenta'))
        if reserva.clase.empezo:
            messages.error(request, 'Esta clase ya empezó, así que no se puede cancelar.')
            return redirect(destino)
        devuelto = cancelar_reserva(reserva)
        if devuelto:
            messages.success(request, 'Cancelaste tu reserva. Tu punto ya está de vuelta en tu cuenta.')
        else:
            messages.info(request, 'Cancelaste tu reserva y liberaste el cupo. Como faltaban menos de '
                                   f'{HORAS_PARA_CANCELAR} horas, el punto no se devuelve.')
        return redirect(destino)


class SimularOcupacionView(View):
    """Prende o apaga el modo "simular ocupación" (solo para esta visita; apagado por defecto)."""

    def post(self, request):
        request.session['simular_ocupacion'] = not simulando(request)
        return redirect(volver_a(request, reverse('horarios')))
