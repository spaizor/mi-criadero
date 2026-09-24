// Las pastillas de seccion de la barra de arriba, iguales en todas las paginas.
//
// Cada HTML lleva escrito el <header class="barra"> con el logo y su enlace a
// la portada, y justo detras este script, que le anade las pastillas. Se
// ejecuta mientras se lee la pagina (sin defer ni fetch), asi que la barra sale
// ya completa en el primer pintado, sin salto.
//
// La lista va aqui y no se lee de assets/secciones.json porque eso seria un
// fetch: la barra apareceria despues que el resto y empujaria la pagina hacia
// abajo. Repetirla es el precio, y 'noticias.py comprobar' vigila que no falte
// ninguna seccion.
//
// La pagina actual se saca de la URL y no del data-seccion del <body>: el
// historico lo cambia al pasar de pestana, y marcaria como actual una seccion
// en la que no se esta.

(function () {
  const SECCIONES = [
    { id: 'tecnologia', nombre: 'Tecnologia', acento: 'tec' },
    { id: 'ia', nombre: 'IA', acento: 'ia' },
    { id: 'nintendo', nombre: 'Nintendo', acento: 'nin' },
    { id: 'geopolitica', nombre: 'Geopolitica', acento: 'geo' },
    { id: 'ofertas', nombre: 'Ofertas', acento: 'ofe' },
    { id: 'steam', nombre: 'Steam', acento: 'ste' },
  ];

  const barra = document.currentScript && document.currentScript.previousElementSibling;
  if (!barra || !barra.classList.contains('barra')) return;

  const actual = location.pathname.split('/').pop().replace(/\.html$/, '');

  const nav = document.createElement('nav');
  nav.className = 'barra-nav';
  nav.setAttribute('aria-label', 'Secciones');
  nav.innerHTML = SECCIONES.map((s) => `
    <a class="${s.acento}" href="${s.id}.html"${s.id === actual ? ' aria-current="page"' : ''}>
      <span class="huevo" aria-hidden="true"></span>${s.nombre}
    </a>`).join('');
  barra.appendChild(nav);

  // En el movil no caben todas: que la actual quede a la vista y no cortada
  // por el borde. Se mueve solo la barra y a mano: scrollIntoView podria
  // desplazar tambien la pagina en vertical.
  const marcada = nav.querySelector('[aria-current]');
  if (marcada) {
    const sobra = marcada.getBoundingClientRect().right - nav.getBoundingClientRect().right;
    if (sobra > 0) nav.scrollLeft += sobra + 20;
  }
})();
