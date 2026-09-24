"""
Acciones de la campanita. Funcionan con JavaScript (sin recargar la página)
y también sin él (vuelven a la página donde estaba).
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


def _responder(request):
    if request.headers.get('X-Requested-With') == 'fetch':
        return JsonResponse({'ok': True, 'sin_leer': request.user.notificaciones.filter(leida=False).count()})
    volver = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    if not url_has_allowed_host_and_scheme(volver, {request.get_host()}, request.is_secure()):
        volver = '/'
    return redirect(volver)


@login_required
@require_POST
def marcar_leidas(request):
    request.user.notificaciones.filter(leida=False).update(leida=True)
    return _responder(request)


@login_required
@require_POST
def borrar(request, pk):
    request.user.notificaciones.filter(pk=pk).delete()   # solo puede borrar las suyas
    return _responder(request)


@login_required
@require_POST
def borrar_todas(request):
    request.user.notificaciones.all().delete()
    return _responder(request)
