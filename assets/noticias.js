// Carga el JSON de una seccion y pinta las noticias.
// El HTML no cambia nunca: las tareas programadas solo reescriben el JSON.

function escapar(texto) {
  const d = document.createElement('div');
  d.textContent = texto == null ? '' : String(texto);
  return d.innerHTML;
}

function pintarNoticia(n) {
  const enlace = n.enlace
    ? ` · <a href="${escapar(n.enlace)}" target="_blank" rel="noopener">Leer mas</a>`
    : '';
  const fuente = n.fuente ? escapar(n.fuente) : 'Sin fuente';
  return `
    <article class="noticia">
      <h2>${escapar(n.titulo)}</h2>
      <p>${escapar(n.resumen)}</p>
      <div class="meta">${fuente}${enlace}</div>
    </article>`;
}

async function cargarNoticias(ruta) {
  const contenedor = document.getElementById('noticias');
  const fecha = document.getElementById('fecha');

  try {
    const resp = await fetch(ruta + '?v=' + Date.now());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const datos = await resp.json();

    fecha.textContent = datos.actualizado
      ? 'Actualizado: ' + datos.actualizado
      : '';

    const noticias = Array.isArray(datos.noticias) ? datos.noticias : [];
    contenedor.innerHTML = noticias.length
      ? noticias.map(pintarNoticia).join('')
      : '<div class="aviso">Todavia no hay noticias en esta seccion.</div>';
  } catch (e) {
    fecha.textContent = '';
    contenedor.innerHTML =
      '<div class="aviso">No se ha podido cargar el contenido.<br>' +
      'Si estas abriendo el archivo en local, usa un servidor web ' +
      '(en GitHub Pages funciona directamente).</div>';
  }
}
