# Publicar el prototipo en PythonAnywhere

Guía para dejar la web en internet (por ejemplo `https://atempo.pythonanywhere.com`)
sin depender de una laptop. Cuenta gratuita: sirve para un prototipo con pocas visitas.

## Antes de empezar
- El código está en GitHub (repositorio `prototipo-web`).
- Hay una cuenta gratuita en https://www.pythonanywhere.com (el nombre de usuario será
  parte de la dirección: `TU_USUARIO.pythonanywhere.com`).

En todo lo que sigue, reemplaza `TU_USUARIO` por ese nombre de usuario.

## 1. Descargar el código (una sola vez)
En PythonAnywhere: pestaña **Consoles** → **Bash**. Pega, una por una:

```bash
git clone https://github.com/USUARIO_GITHUB/prototipo-web.git
cd prototipo-web
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(Si el repositorio es privado, GitHub pedirá usuario y un "token" en lugar de la contraseña.)

Si `python3.13` no existe en tu cuenta, usa la versión más nueva que aparezca (3.10 o más), por ejemplo `python3.12`, y elige esa misma versión en el paso 3.

## 2. Crear la base de datos y el usuario del panel (una sola vez)
En la misma consola:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

- `createsuperuser` pide correo, nombre, apellido y contraseña: es el acceso al panel
  (`/admin/`). Compártelo solo con el equipo.
- El último comando muestra una **clave secreta**: cópiala para el paso 3. No la subas a
  GitHub ni la compartas.

## 3. Crear la web (una sola vez)
Pestaña **Web** → **Add a new web app** → **Manual configuration** (no "Django") →
**Python 3.13**. Luego, en esa misma pestaña:

1. **Virtualenv**: `/home/TU_USUARIO/prototipo-web/.venv`
2. **WSGI configuration file**: abrirlo, borrar todo y pegar el contenido de
   `despliegue/wsgi_pythonanywhere.py`, reemplazando `TU_USUARIO` y `CLAVE_SECRETA`.
3. **Static files**: URL `/static/` → Directory `/home/TU_USUARIO/prototipo-web/staticfiles`
4. **Force HTTPS**: activado.
5. Botón verde **Reload**.

Listo: la web queda en `https://TU_USUARIO.pythonanywhere.com`.

## Cada vez que hay cambios nuevos
En la consola Bash de PythonAnywhere:

```bash
cd ~/prototipo-web
source .venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Y en la pestaña **Web**, botón **Reload**.

## Mantenimiento
- Cuenta gratuita: cada 3 meses, entrar a la pestaña **Web** y pulsar
  **"Run until 3 months from today"**. Si no, la web se apaga (no se pierde nada; se
  vuelve a encender con el mismo botón).
- La base de datos del servidor es independiente de la de la laptop: lo que se cambie en el
  panel publicado se queda ahí.
- Todo el que tenga el enlace puede entrar, y la cuenta de demostración entra sin
  contraseña. **No usar datos reales de personas.**

## Si algo falla
Pestaña **Web** → **Error log** (al final de la página): muestra el motivo.
