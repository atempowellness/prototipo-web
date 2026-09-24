"""
Permite iniciar sesión con el correo o con el celular, siempre con contraseña.
"""
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CorreoOCelularBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        Usuario = get_user_model()
        identificador = username.strip()
        digitos = re.sub(r'\D', '', identificador)
        try:
            if '@' in identificador:
                usuario = Usuario.objects.get(email__iexact=identificador)
            elif digitos:
                usuario = Usuario.objects.get(celular=digitos)
            else:
                return None
        except Usuario.DoesNotExist:
            Usuario().set_password(password)  # mismo tiempo de respuesta exista o no
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
