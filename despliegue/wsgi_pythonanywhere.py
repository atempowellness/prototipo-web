# =============================================================================
# Archivo de arranque para PythonAnywhere (MODELO).
#
# En PythonAnywhere: pestaña "Web" -> "WSGI configuration file" -> borrar todo
# y pegar este contenido, reemplazando:
#   TU_USUARIO     -> tu nombre de usuario de PythonAnywhere
#   CLAVE_SECRETA  -> la clave que genera el comando de los pasos de despliegue
#
# La clave secreta NO se sube a GitHub: solo vive en este archivo del servidor.
# =============================================================================
import os
import sys

proyecto = '/home/TU_USUARIO/prototipo-web'
if proyecto not in sys.path:
    sys.path.insert(0, proyecto)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['DJANGO_DEBUG'] = '0'
os.environ['DJANGO_SECRET_KEY'] = 'CLAVE_SECRETA'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'TU_USUARIO.pythonanywhere.com'

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
