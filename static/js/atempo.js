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

  prefiereOscuro.addEventListener('change', actualizarBoton);
  actualizarBoton();
})();

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
