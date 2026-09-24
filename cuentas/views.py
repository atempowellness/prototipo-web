from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode
from django.views.generic import FormView, TemplateView

from .forms import IngresarForm, NuevaClaveForm, RecuperarForm, RegistroForm


def destino_seguro(request, por_defecto='cuenta'):
    """La página a la que volver después de ingresar (?next=...), solo si es de este sitio."""
    siguiente = request.POST.get('next') or request.GET.get('next')
    if siguiente and url_has_allowed_host_and_scheme(siguiente, {request.get_host()}, request.is_secure()):
        return siguiente
    return reverse(por_defecto)


class RegistroView(FormView):
    template_name = 'cuentas/registro.html'
    form_class = RegistroForm
    extra_context = {'titulo': 'Crear cuenta'}

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(destino_seguro(request))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        # El enlace para compartir por WhatsApp trae el código: /cuenta/registro/?codigo=MARIA-7K3Q
        return {'codigo_referida': self.request.GET.get('codigo', '')}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['next'] = self.request.POST.get('next') or self.request.GET.get('next', '')
        return contexto

    def form_valid(self, form):
        from notificaciones import avisos

        usuario = form.save()
        avisos.bienvenida(usuario)
        if usuario.referida_por:
            avisos.amiga_se_registro(usuario.referida_por, usuario)
        login(self.request, usuario, backend='cuentas.backends.CorreoOCelularBackend')
        messages.success(self.request, f'¡Bienvenida a Atempo, {usuario.nombre}! Tu cuenta está lista.')
        return redirect(destino_seguro(self.request))


class IngresarView(auth_views.LoginView):
    template_name = 'cuentas/ingresar.html'
    authentication_form = IngresarForm
    redirect_authenticated_user = True
    extra_context = {'titulo': 'Iniciar sesión'}

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f'¡Hola de nuevo, {form.get_user().nombre}!')
        return respuesta


class SalirView(auth_views.LogoutView):
    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        messages.info(request, 'Cerraste sesión. ¡Te esperamos pronto!')
        return respuesta


class MiCuentaView(LoginRequiredMixin, TemplateView):
    template_name = 'cuentas/mi_cuenta.html'
    extra_context = {'titulo': 'Mi cuenta'}

    def get_context_data(self, **kwargs):
        from urllib.parse import quote

        from compras.models import compras_pagadas, compras_vigentes, creditos_disponibles, tiene_atempo_circle
        from compras.referidas import TOPE_MENSUAL, estado_de_invitadas, regalos_del_mes

        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        vigentes = list(compras_vigentes(usuario))

        # Programa de referidas
        enlace = self.request.build_absolute_uri(reverse('registro') + f'?codigo={usuario.codigo_referida}')
        mensaje = (f'Te invito a Atempo Wellness, un estudio boutique de bienestar en San Isidro. '
                   f'Usa mi código {usuario.codigo_referida} al comprar tu primer paquete desde Atempo 5 '
                   f'y las dos recibimos 1 clase extra: {enlace}')
        from clases.servicios import proximas_reservas
        contexto['proximas_reservas'] = proximas_reservas(usuario)

        regalos_mes = regalos_del_mes(usuario).count()
        contexto.update({
            'enlace_referida': enlace,
            'whatsapp_referida': 'https://wa.me/?text=' + quote(mensaje),
            'invitadas': estado_de_invitadas(usuario),
            'regalos_mes': regalos_mes,
            'tope_referidas': TOPE_MENSUAL,
            'tope_alcanzado': regalos_mes >= TOPE_MENSUAL,
        })
        contexto.update({
            'compras_vigentes': [c for c in vigentes if c.creditos_disponibles > 0 or
                                 c.nutricion_disponible > 0 or c.masaje_disponible > 0],
            'creditos_totales': creditos_disponibles(usuario),
            'nutricion_total': sum(c.nutricion_disponible for c in vigentes),
            'masaje_total': sum(c.masaje_disponible for c in vigentes),
            'tiene_circle': tiene_atempo_circle(usuario),
            'por_vencer': [c for c in vigentes if c.vence_pronto],
            'historial': compras_pagadas(usuario),
        })
        return contexto


class RecuperarView(FormView):
    """
    SIMULACIÓN: en lugar de enviar un correo, muestra en la misma página cómo se
    vería el correo con el enlace para crear una nueva contraseña. En la versión
    real, el enlace solo llegaría al correo de la dueña de la cuenta.
    """
    template_name = 'cuentas/recuperar.html'
    form_class = RecuperarForm
    extra_context = {'titulo': 'Recuperar contraseña'}

    def form_valid(self, form):
        Usuario = get_user_model()
        email = form.cleaned_data['email']
        usuario = Usuario.objects.filter(email__iexact=email, is_active=True).first()
        contexto = self.get_context_data(form=form, email=email)
        if usuario:
            ruta = reverse('nueva_clave', kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(usuario.pk)),
                'token': default_token_generator.make_token(usuario),
            })
            contexto['correo_simulado'] = {
                'nombre': usuario.nombre,
                'enlace': self.request.build_absolute_uri(ruta),
                'ruta': ruta,
            }
        else:
            contexto['no_encontrado'] = True
        return self.render_to_response(contexto)


class NuevaClaveView(auth_views.PasswordResetConfirmView):
    template_name = 'cuentas/nueva_clave.html'
    form_class = NuevaClaveForm
    success_url = reverse_lazy('ingresar')
    extra_context = {'titulo': 'Nueva contraseña'}

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, 'Listo, tu contraseña cambió. Ya puedes ingresar con la nueva.')
        return respuesta
