"""
Datos que se agregan automáticamente a todas las plantillas.
"""
from django.conf import settings

ARCHIVOS_COMPARTIDOS = ['css/atempo.css', 'js/atempo.js', 'css/panel.css']


def datos_estudio(request):
    """Datos de la empresa que se muestran en varias páginas (pie, boleta, páginas legales)."""
    from .views import CORREO, DIRECCION, RAZON_SOCIAL, RUC, WHATSAPP
    return {'direccion_estudio': DIRECCION, 'razon_social': RAZON_SOCIAL, 'ruc': RUC,
            'correo_estudio': CORREO, 'whatsapp_estudio': WHATSAPP}


def version_estaticos(request):
    """
    Número de versión de la hoja de estilos y del script, basado en la fecha
    en que se modificaron por última vez. Se agrega a sus direcciones
    (por ejemplo atempo.css?v=1727100000) para que el navegador descargue la
    versión nueva cada vez que cambian, en lugar de usar una copia guardada.
    """
    carpeta = settings.BASE_DIR / 'static'
    version = max(
        int((carpeta / archivo).stat().st_mtime) for archivo in ARCHIVOS_COMPARTIDOS
    )
    return {'version_estaticos': version}
