// El numero de version del pie y el panel que cuenta que trae cada una.
//
// La version vive SOLO en assets/version.json. Escribirla ademas en el HTML
// obligaria a tocar las ocho paginas cada vez que sube, que es justo la clase
// de trabajo repetido que este proyecto evita: subir de version es anadir una
// entrada a un JSON y nada mas.
//
// Si el fetch falla, el pie se queda como estaba y no sale el enlace. Es lo
// contrario de lo que hace la portada, que lleva sus entradas escritas en el
// HTML para no quedarse en blanco, y la diferencia es deliberada: alli lo que se
// protege es el contenido de la pagina, y aqui lo que se perderia es una nota
// al pie. Una version a medias o equivocada seria peor que ninguna.

const RUTA_VERSION = 'assets/version.json';

function escaparVersion(texto) {
  return String(texto == null ? '' : texto)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function pintarPanel(historial) {
  const partes = historial.map((v, i) => `
    <section class="version-bloque${i === 0 ? ' actual' : ''}">
      <h3>
        <span class="version-num">${escaparVersion(v.version)}</span>
        ${escaparVersion(v.titulo)}
        <span class="version-fecha">${escaparVersion(v.fecha)}</span>
      </h3>
      <ul>${(v.cambios || []).map(
        (c) => `<li>${escaparVersion(c)}</li>`).join('')}</ul>
    </section>`);

  // <dialog> nativo y no un div montado a mano: trae gratis el cierre con
  // Escape, el foco atrapado dentro mientras esta abierto y el fondo inerte.
  const panel = document.createElement('dialog');
  panel.className = 'version-panel';
  panel.innerHTML = `
    <div class="version-cabecera">
      <strong>Que hay de nuevo</strong>
      <button class="version-cerrar" type="button" aria-label="Cerrar">✕</button>
    </div>
    ${partes.join('')}`;

  panel.querySelector('.version-cerrar')
       .addEventListener('click', () => panel.close());
  // Pulsar el fondo cierra. El click en el backdrop lo recibe el propio
  // <dialog>, asi que se mira si cayo fuera de su caja.
  panel.addEventListener('click', (e) => {
    const caja = panel.getBoundingClientRect();
    const fuera = e.clientX < caja.left || e.clientX > caja.right ||
                  e.clientY < caja.top || e.clientY > caja.bottom;
    if (fuera) panel.close();
  });
  return panel;
}

async function cargarVersion() {
  const pie = document.querySelector('.pie');
  if (!pie) return;

  let datos;
  try {
    const resp = await fetch(RUTA_VERSION);
    if (!resp.ok) return;
    datos = await resp.json();
  } catch (e) {
    return;
  }

  const historial = Array.isArray(datos.historial) ? datos.historial : [];
  if (!historial.length) return;

  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'version';
  boton.textContent = 'v' + historial[0].version;
  boton.title = 'Ver que trae cada version';

  const panel = pintarPanel(historial);
  document.body.appendChild(panel);
  boton.addEventListener('click', () => panel.showModal());

  pie.appendChild(boton);
}

cargarVersion();
