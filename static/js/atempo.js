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
