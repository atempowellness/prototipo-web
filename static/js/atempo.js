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

/* ---------- Filtros y días sin recargar la página ----------
   Dentro de una zona marcada con data-zona (el horario de clases, la agenda de
   nutrición y masajes), los enlaces que solo cambian los filtros ("?dia=…")
   actualizan esa zona sin mover la posición de la pantalla. La dirección de la
   página se actualiza igual, así funcionan el botón "atrás" y los enlaces compartidos.
   Si algo falla, se abre la página de la forma normal. */
(function () {
  function actualizarZona(url, id, guardarEnHistorial) {
    var zona = document.getElementById(id);
    if (!zona) { window.location.href = url; return; }
    zona.classList.add('zona-cargando');
    fetch(url, { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error(); return r.text(); })
      .then(function (html) {
        var nueva = new DOMParser().parseFromString(html, 'text/html').getElementById(id);
        if (!nueva) throw new Error();
        zona.replaceWith(nueva);
        if (guardarEnHistorial) history.pushState({ zona: id }, '', url);
      })
      .catch(function () { window.location.href = url; });
  }

  document.addEventListener('click', function (e) {
    var enlace = e.target.closest('[data-zona] a[href^="?"]');
    if (!enlace || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    actualizarZona(enlace.href, enlace.closest('[data-zona]').id, true);
  });

  // Botón "atrás" / "adelante" del navegador
  window.addEventListener('popstate', function (e) {
    if (e.state && e.state.zona) actualizarZona(window.location.href, e.state.zona, false);
  });
  var zona = document.querySelector('[data-zona]');
  if (zona) history.replaceState({ zona: zona.id }, '', window.location.href);
})();

/* ---------- Libro de reclamaciones: "Completar con datos de prueba" (para la demostración) ----------
   Solo llena los campos vacíos, así respeta los datos que ya vienen de la cuenta. */
(function () {
  var boton = document.querySelector('[data-datos-prueba-reclamo]');
  if (!boton) return;
  boton.addEventListener('click', function () {
    var datos = {
      nombre: 'María Salas', dni: '45678912', telefono: '987654321', email: 'maria@correo.pe',
      domicilio: 'Av. Ejemplo 123, San Isidro, Lima', servicio: 'clase', monto: '',
      descripcion_servicio: 'Clase de Pilates del lunes a las 7:30',
      detalle: 'La clase empezó 20 minutos tarde y no se avisó con anticipación.',
      pedido: 'Que me devuelvan el punto usado en esa clase.'
    };
    Object.keys(datos).forEach(function (nombre) {
      var campo = boton.form.querySelector('[name="' + nombre + '"]');
      if (campo && !campo.value) campo.value = datos[nombre];
    });
    var reclamo = boton.form.querySelector('input[name="tipo"][value="reclamo"]');
    if (reclamo && !boton.form.querySelector('input[name="tipo"]:checked')) reclamo.checked = true;
    var acepto = boton.form.querySelector('[name="acepto"]');
    if (acepto) acepto.checked = true;
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

/* ---------- Nosotros: agradecimiento a las fundadoras ----------
   Los nombres rotan en tandas con un fundido. El intervalo sale de
   --intervalo-muro (atempo.css). Puntos para elegir tanda y botón "Pausar".
   Con "reducir movimiento" no cambian solas. Sin JavaScript se ven todas. */
(function () {
  var muro = document.querySelector('[data-muro]');
  if (!muro) return;
  var tandas = muro.querySelectorAll('.muro-tanda');
  var controles = document.querySelector('[data-muro-controles]');
  if (tandas.length < 2 || !controles) return;

  var puntos = controles.querySelectorAll('.muro-punto');
  var pausa = controles.querySelector('.muro-pausa');
  var intervalo = parseFloat(getComputedStyle(document.documentElement)
    .getPropertyValue('--intervalo-muro')) || 6000;
  var actual = 0;
  var temporizador = null;

  muro.classList.add('muro-animado');
  controles.hidden = false;

  function mostrar(n) {
    tandas[actual].classList.remove('activa');
    puntos[actual].removeAttribute('aria-current');
    actual = (n + tandas.length) % tandas.length;
    tandas[actual].classList.add('activa');
    puntos[actual].setAttribute('aria-current', 'true');
  }

  function iniciar() {
    detener();
    temporizador = setInterval(function () { mostrar(actual + 1); }, intervalo);
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
      if (temporizador) iniciar();
    });
  });
  pausa.addEventListener('click', function () {
    if (temporizador) detener(); else iniciar();
  });

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) detener(); else iniciar();
})();

/* ---------- Desplegables que se abren y cierran suavemente ----------
   Preguntas frecuentes, "Ver detalles" de paquetes, reclamos y ayudas.
   La duración sale de --duracion-desplegable (atempo.css). La campanita no
   se anima (es un menú). Sin JavaScript o con "reducir movimiento", se
   abren al instante como siempre. */
(function () {
  if (!document.body.animate) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var duracion = parseFloat(getComputedStyle(document.documentElement)
    .getPropertyValue('--duracion-desplegable')) || 300;

  document.addEventListener('click', function (evento) {
    var resumen = evento.target.closest('summary');
    if (!resumen) return;
    var desplegable = resumen.parentElement;
    if (desplegable.tagName !== 'DETAILS' || desplegable.matches('[data-campanita]')) return;
    evento.preventDefault();

    // Si estaba a medio animar, se parte desde la altura actual
    var altoInicial = desplegable.offsetHeight;
    if (desplegable._animacion) desplegable._animacion.cancel();
    var abriendo = !desplegable.open || desplegable._cerrando;
    desplegable._cerrando = !abriendo;

    // Se mide cómo queda cerrado y abierto (no se alcanza a ver en pantalla)
    desplegable.open = false;
    var altoCerrado = desplegable.offsetHeight;
    desplegable.open = true;
    var altoFinal = abriendo ? desplegable.offsetHeight : altoCerrado;

    desplegable.style.overflow = 'hidden';
    var animacion = desplegable.animate(
      { height: [altoInicial + 'px', altoFinal + 'px'] },
      { duration: duracion, easing: 'ease' }
    );
    desplegable._animacion = animacion;
    animacion.onfinish = function () {
      desplegable.open = abriendo;
      desplegable._animacion = null;
      desplegable._cerrando = false;
      desplegable.style.overflow = '';
    };
  });
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
