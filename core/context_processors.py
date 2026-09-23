"""
Datos que se agregan automáticamente a todas las plantillas.
"""
from django.conf import settings

ARCHIVOS_COMPARTIDOS = ['css/atempo.css', 'js/atempo.js']


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
