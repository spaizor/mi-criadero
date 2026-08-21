// Carga el JSON de una seccion y pinta las noticias.
// El HTML no cambia nunca: las tareas programadas solo reescriben el JSON.
//
// Dos niveles: "destacadas" (con resumen, se leyeron enteras) y "titulares"
// (solo titular y enlace, sacados del listado del medio).
// Se acepta tambien el formato antiguo con "noticias" como respaldo, para que
// la web no se quede en blanco entre que se publica un cambio aqui y corre la
// primera rutina con el formato nuevo.

function escapar(texto) {
  const d = document.createElement('div');
  d.textContent = texto == null ? '' : String(texto);
  return d.innerHTML;
}

function pintarDestacada(n, indice) {
  const enlace = n.enlace
    ? ` · <a href="${escapar(n.enlace)}" target="_blank" rel="noopener">Leer mas</a>`
    : '';
  const fecha = n.fecha ? ` · ${escapar(n.fecha)}` : '';
  const fuente = n.fuente ? escapar(n.fuente) : 'Sin fuente';
  return `
    <article class="noticia">
      <h2><span class="num">${indice + 1}</span>${escapar(n.titulo)}</h2>
      <p>${escapar(n.resumen)}</p>
      <div class="meta">${fuente}${fecha}${enlace}</div>
    </article>`;
}

function pintarTitular(n) {
  const titulo = escapar(n.titulo);
  const titular = n.enlace
    ? `<a href="${escapar(n.enlace)}" target="_blank" rel="noopener">${titulo}</a>`
    : titulo;
  const fecha = n.fecha ? ` · ${escapar(n.fecha)}` : '';
  const fuente = n.fuente ? escapar(n.fuente) : 'Sin fuente';
  return `
    <li class="titular">
      ${titular}
      <span class="meta">${fuente}${fecha}</span>
    </li>`;
}

function pintarTitulares(titulares) {
  if (!titulares.length) return '';
  const palabra = titulares.length === 1 ? 'titular' : 'titulares';
  return `
    <details class="mas-titulares">
      <summary>Ver los otros ${titulares.length} ${palabra} del dia</summary>
      <ul class="lista-titulares">${titulares.map(pintarTitular).join('')}</ul>
    </details>`;
}

// La portada marca "nuevo" comparando el 'actualizado' de cada seccion con el
// que se apunto la ultima vez que se abrio. Se apunta aqui y no al pulsar la
// tarjeta porque lo que cuenta como visto es haber entrado y que el turno haya
// cargado, no haber hecho clic.
//
// La clave es la misma que lee assets/portada.js. Si se cambia, cambiarla ahi.
// El almacenamiento puede estar capado (ventana privada, ajustes del movil):
// que se pierda la marca no importa, que reviente la seccion si.
function apuntarVisto(seccion, actualizado) {
  if (!seccion || !actualizado) return;
  try {
    localStorage.setItem('visto:' + seccion, actualizado);
  } catch (e) {
    /* sin marca, la portada dira "nuevo" de mas: es el fallo bueno */
  }
}

// 'seccion' solo lo pasan las paginas de seccion. El historico llama sin el:
// mirar un turno de hace tres dias no es haber leido el de hoy.
async function cargarNoticias(ruta, seccion) {
  const contenedor = document.getElementById('noticias');
  const fecha = document.getElementById('fecha');

  try {
    const resp = await fetch(ruta + '?v=' + Date.now());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const datos = await resp.json();

    apuntarVisto(seccion, datos.actualizado);

    fecha.textContent = datos.actualizado
      ? 'Actualizado: ' + datos.actualizado
      : '';

    // "noticias" es el formato antiguo; se mantiene como respaldo.
    let destacadas = [];
    if (Array.isArray(datos.destacadas)) destacadas = datos.destacadas;
    else if (Array.isArray(datos.noticias)) destacadas = datos.noticias;

    const titulares = Array.isArray(datos.titulares) ? datos.titulares : [];

    contenedor.innerHTML = (destacadas.length || titulares.length)
      ? destacadas.map(pintarDestacada).join('') + pintarTitulares(titulares)
      : '<div class="aviso">Todavia no hay noticias en esta seccion.</div>';
  } catch (e) {
    fecha.textContent = '';
    contenedor.innerHTML =
      '<div class="aviso">No se ha podido cargar el contenido.<br>' +
      'Si estas abriendo el archivo en local, usa un servidor web ' +
      '(en GitHub Pages funciona directamente).</div>';
  }
}
