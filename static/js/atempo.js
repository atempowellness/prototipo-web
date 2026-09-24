/* =========================================================
   Atempo Wellness - comportamiento compartido por todo el sitio
   ========================================================= */

/* ---------- Menú en celular: abrir y cerrar ---------- */
(function () {
  var boton = document.querySelector('.boton-menu');
  var menu = document.getElementById('menu-principal');
  if (!boton || !menu) return;

  boton.addEventListener('click', function () {
    var abierto = menu.classList.toggle('abierto');
    boton.setAttribute('aria-expanded', abierto ? 'true' : 'false');
  });
})();

/* ---------- Tema claro / oscuro ----------
   Al entrar se usa el tema del dispositivo. Si la persona
   lo cambia con el botón, su elección se recuerda. */
(function () {
  var boton = document.querySelector('.boton-tema');
  if (!boton) return;
  var raiz = document.documentElement;
  var prefiereOscuro = window.matchMedia('(prefers-color-scheme: dark)');

  function temaActual() {
    return raiz.dataset.theme || (prefiereOscuro.matches ? 'dark' : 'light');
  }

  function actualizarBoton() {
    boton.textContent = temaActual() === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro';
  }

  boton.addEventListener('click', function () {
    var nuevo = temaActual() === 'dark' ? 'light' : 'dark';
    raiz.dataset.theme = nuevo;
    try { localStorage.setItem('atempo-tema', nuevo); } catch (e) {}
    actualizarBoton();
  });

  // Si la persona no eligió un tema, seguir los cambios del dispositivo
  prefiereOscuro.addEventListener('change', function () {
    var elegido = null;
    try { elegido = localStorage.getItem('atempo-tema'); } catch (e) {}
    if (!elegido) raiz.dataset.theme = prefiereOscuro.matches ? 'dark' : 'light';
    actualizarBoton();
  });
  actualizarBoton();
})();

/* ---------- Contraseñas: botón "Mostrar" / "Ocultar" ---------- */
document.querySelectorAll('.boton-mostrar').forEach(function (boton) {
  var campo = document.getElementById(boton.getAttribute('aria-controls'));
  if (!campo) return;
  boton.addEventListener('click', function () {
    var mostrar = campo.type === 'password';
    campo.type = mostrar ? 'text' : 'password';
    boton.textContent = mostrar ? 'Ocultar' : 'Mostrar';
    boton.setAttribute('aria-pressed', mostrar ? 'true' : 'false');
  });
});

/* ---------- Pago: mostrar solo los campos del método elegido ----------
   Sin JavaScript se ven todos los campos y el formulario igual funciona. */
(function () {
  var opciones = document.querySelectorAll('input[name="metodo"]');
  var grupos = document.querySelectorAll('.metodo-campos');
  if (!opciones.length) return;

  function metodoElegido() {
    var marcado = document.querySelector('input[name="metodo"]:checked');
    return marcado ? marcado.value : 'tarjeta';
  }

  function actualizar() {
    var metodo = metodoElegido();
    grupos.forEach(function (grupo) {
      grupo.hidden = grupo.dataset.metodo.split(' ').indexOf(metodo) === -1;
    });
  }

  opciones.forEach(function (opcion) { opcion.addEventListener('change', actualizar); });
  actualizar();

  // "Completar con datos de prueba" (para la demostración)
  var prueba = document.querySelector('[data-datos-prueba]');
  if (prueba) {
    prueba.addEventListener('click', function () {
      var datos = {
        tarjeta: { tarjeta_numero: '4111 1111 1111 1111', tarjeta_vence: '12/29', tarjeta_cvv: '123' },
        yape: { celular: '912 345 678', codigo_yape: '123456' },
        plin: { celular: '912 345 678' }
      }[metodoElegido()];
      Object.keys(datos).forEach(function (nombre) {
        var campo = document.querySelector('[name="' + nombre + '"]');
        if (campo) campo.value = datos[nombre];
      });
    });
  }
})();

/* ---------- Campanita de notificaciones ----------
   Al abrirla, las notificaciones pasan a leídas. Borrar una o todas no recarga
   la página. Se cierra al tocar fuera o con Esc. */
(function () {
  var campanita = document.querySelector('[data-campanita]');
  if (!campanita) return;

  function enviar(formulario) {
    return fetch(formulario.action, {
      method: 'POST',
      body: new FormData(formulario),
      headers: { 'X-Requested-With': 'fetch' },
      credentials: 'same-origin'
    }).then(function (r) { return r.json(); });
  }

  function actualizarVacia() {
    var quedan = campanita.querySelectorAll('[data-aviso]').length;
    campanita.querySelector('[data-vacia]').hidden = quedan > 0;
    var todas = campanita.querySelector('[data-borrar-todas]');
    if (todas) todas.hidden = quedan === 0;
  }

  campanita.addEventListener('toggle', function () {
    if (!campanita.open) return;
    var contador = campanita.querySelector('[data-contador]');
    if (contador) {
      enviar(campanita.querySelector('[data-marcar-leidas]')).then(function () {
        contador.remove();
        campanita.querySelector('.campanita-boton').setAttribute('aria-label', 'Notificaciones');
      });
    }
  });

  campanita.querySelectorAll('[data-borrar]').forEach(function (formulario) {
    formulario.addEventListener('submit', function (e) {
      e.preventDefault();
      enviar(formulario).then(function () {
        formulario.closest('[data-aviso]').remove();
        actualizarVacia();
      });
    });
  });

  var borrarTodas = campanita.querySelector('[data-borrar-todas]');
  if (borrarTodas) {
    borrarTodas.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!window.confirm('¿Borrar todas tus notificaciones? No se puede deshacer.')) return;
      enviar(borrarTodas).then(function () {
        campanita.querySelectorAll('[data-aviso]').forEach(function (li) { li.remove(); });
        actualizarVacia();
      });
    });
  }

  document.addEventListener('click', function (e) {
    if (campanita.open && !campanita.contains(e.target)) campanita.open = false;
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && campanita.open) {
      campanita.open = false;
      campanita.querySelector('summary').focus();
    }
  });
})();

/* ---------- Ventana de confirmación (reservar y cancelar clases) ----------
   Los enlaces con data-dialogo cargan su confirmación dentro de una ventana sobre
   la página. Sin JavaScript (o si algo falla), el enlace abre la página de siempre. */
(function () {
  var dialogo = document.querySelector('[data-dialogo-contenedor]');
  if (!dialogo || typeof dialogo.showModal !== 'function') return;
  var cuerpo = dialogo.querySelector('[data-dialogo-cuerpo]');

  document.addEventListener('click', function (e) {
    var enlace = e.target.closest('a[data-dialogo]');
    if (enlace) {
      e.preventDefault();
      var url = enlace.href + (enlace.href.indexOf('?') === -1 ? '?' : '&') + 'parcial=1';
      fetch(url, { credentials: 'same-origin' }).then(function (r) {
        // Si pide iniciar sesión (u otra redirección), se va a la página normal
        if (r.redirected || !r.ok) { window.location.href = enlace.href; return null; }
        return r.text();
      }).then(function (html) {
        if (html === null || html === undefined) return;
        cuerpo.innerHTML = html;
        dialogo.showModal();
      }).catch(function () { window.location.href = enlace.href; });
      return;
    }
    if (e.target.closest('[data-cerrar-dialogo]')) dialogo.close();
  });

  // Cerrar al tocar fuera de la ventana
  dialogo.addEventListener('click', function (e) {
    if (e.target === dialogo) dialogo.close();
  });
})();

/* ---------- Botones "Copiar" (por ejemplo, el código de referida) ---------- */
document.querySelectorAll('[data-copiar]').forEach(function (boton) {
  var textoOriginal = boton.textContent;
  boton.addEventListener('click', function () {
    var listo = function () {
      boton.textContent = '¡Copiado!';
      setTimeout(function () { boton.textContent = textoOriginal; }, 2000);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(boton.dataset.copiar).then(listo, function () {
        boton.textContent = 'Tu código: ' + boton.dataset.copiar;
      });
    } else {
      boton.textContent = 'Tu código: ' + boton.dataset.copiar;
    }
  });
});

/* ---------- Portada: imágenes que cambian solas ----------
   Cambian cada 6 segundos con un fundido. Los puntos permiten elegir
   una imagen y el botón "Pausar" detiene el cambio. Si la persona pidió
   "reducir movimiento", las imágenes no cambian solas. */
(function () {
  var diapos = document.querySelectorAll('.portada-diapo');
  var puntos = document.querySelectorAll('.portada-punto');
  var pausa = document.querySelector('.portada-pausa');
  if (diapos.length < 2) return;

  var actual = 0;
  var temporizador = null;
  var reducirMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function mostrar(n) {
    diapos[actual].classList.remove('activa');
    puntos[actual].removeAttribute('aria-current');
    actual = (n + diapos.length) % diapos.length;
    diapos[actual].classList.add('activa');
    puntos[actual].setAttribute('aria-current', 'true');
  }

  function iniciar() {
    detener();
    temporizador = setInterval(function () { mostrar(actual + 1); }, 6000);
    pausa.textContent = 'Pausar';
  }

  function detener() {
    clearInterval(temporizador);
    temporizador = null;
    pausa.textContent = 'Reanudar';
  }

  puntos.forEach(function (punto, i) {
    punto.addEventListener('click', function () {
      mostrar(i);
      if (temporizador) iniciar();   // reinicia la cuenta de 6 segundos
    });
  });

  pausa.addEventListener('click', function () {
    if (temporizador) detener(); else iniciar();
  });

  if (reducirMovimiento) detener(); else iniciar();
})();

/* ---------- Franjas de imagen con efecto de profundidad ----------
   La imagen se desplaza más lento que la página al hacer scroll.
   Se desactiva si la persona pidió "reducir movimiento". */
(function () {
  var fondos = document.querySelectorAll('.franja-imagen-fondo');
  if (!fondos.length) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var pendiente = false;

  function mover() {
    var alto = window.innerHeight;
    fondos.forEach(function (fondo) {
      var caja = fondo.parentElement.getBoundingClientRect();
      if (caja.bottom < 0 || caja.top > alto) return;
      // -1 cuando la franja entra por abajo, 1 cuando sale por arriba
      var avance = (alto - caja.top) / (alto + caja.height) * 2 - 1;
      fondo.style.transform = 'translateY(' + (avance * 10) + '%)';
    });
    pendiente = false;
  }

  window.addEventListener('scroll', function () {
    if (!pendiente) {
      pendiente = true;
      window.requestAnimationFrame(mover);
    }
  }, { passive: true });

  mover();
})();
