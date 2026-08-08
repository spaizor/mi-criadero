// Carga data/ofertas.json y pinta un bloque por producto con el precio de cada
// tienda. Igual que en las noticias, el HTML no cambia nunca: el JSON lo
// reescribe scripts/precios.py en cada ejecucion.
//
// Un precio puede venir en tres estados:
//   ok    -> consultado en esta ejecucion
//   viejo -> la tienda no respondio y se conserva el anterior, avisando
//   nuevo -> producto recien anadido, todavia sin consultar

function escaparOferta(texto) {
  const d = document.createElement('div');
  d.textContent = texto == null ? '' : String(texto);
  return d.innerHTML;
}

function formatearPrecio(valor, moneda) {
  const numero = Number(valor).toFixed(2).replace('.', ',');
  return numero + ' ' + (moneda === 'EUR' || !moneda ? '€' : escaparOferta(moneda));
}

function pintarPrecio(p, esMasBarato) {
  if (p.precio == null) {
    return `
      <li class="precio">
        <span class="tienda">${escaparOferta(p.tienda)}</span>
        <span class="importe sin-dato">Sin consultar</span>
      </li>`;
  }

  const etiquetas = [];
  if (esMasBarato) etiquetas.push('<span class="etiqueta barato">Mas barato</span>');
  if (p.estado === 'viejo') {
    etiquetas.push('<span class="etiqueta viejo">No responde: ultimo precio conocido</span>');
  }
  if (p.disponible === false) {
    etiquetas.push('<span class="etiqueta agotado">Sin stock</span>');
  }
  if (p.vendedor) {
    etiquetas.push(`<span class="etiqueta">Vende ${escaparOferta(p.vendedor)}</span>`);
  }

  const minimo = (p.minimo != null && p.minimo < p.precio)
    ? `<span class="minimo">Minimo visto: ${formatearPrecio(p.minimo, p.moneda)}${
        p.minimo_fecha ? ' · ' + escaparOferta(p.minimo_fecha) : ''}</span>`
    : (p.minimo != null
        ? '<span class="minimo">Es el minimo que hemos visto</span>'
        : '');

  const tienda = p.enlace
    ? `<a href="${escaparOferta(p.enlace)}" target="_blank" rel="noopener">${escaparOferta(p.tienda)}</a>`
    : escaparOferta(p.tienda);

  return `
    <li class="precio${esMasBarato ? ' destacado' : ''}">
      <span class="tienda">${tienda}</span>
      <span class="importe">${formatearPrecio(p.precio, p.moneda)}</span>
      <span class="detalles">${etiquetas.join('')}${minimo}</span>
    </li>`;
}

function pintarProducto(producto) {
  const precios = Array.isArray(producto.precios) ? producto.precios : [];
  const validos = precios.filter(p => p.precio != null);
  const barato = validos.length > 1
    ? Math.min(...validos.map(p => p.precio))
    : null;

  const filas = precios.length
    ? precios.map(p => pintarPrecio(p, barato != null && p.precio === barato)).join('')
    : '<li class="precio"><span class="importe sin-dato">Sin tiendas configuradas</span></li>';

  return `
    <article class="producto">
      <h2>${escaparOferta(producto.nombre)}</h2>
      ${producto.plataforma ? `<p class="plataforma">${escaparOferta(producto.plataforma)}</p>` : ''}
      <ul class="lista-precios">${filas}</ul>
    </article>`;
}

async function cargarOfertas(ruta) {
  const contenedor = document.getElementById('ofertas');
  const fecha = document.getElementById('fecha');

  try {
    const resp = await fetch(ruta + '?v=' + Date.now());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const datos = await resp.json();

    fecha.textContent = datos.actualizado
      ? 'Precios consultados: ' + datos.actualizado
      : '';

    const productos = Array.isArray(datos.productos) ? datos.productos : [];
    contenedor.innerHTML = productos.length
      ? productos.map(pintarProducto).join('')
      : '<div class="aviso">Todavia no hay productos en seguimiento.</div>';
  } catch (e) {
    fecha.textContent = '';
    contenedor.innerHTML =
      '<div class="aviso">No se ha podido cargar el contenido.<br>' +
      'Si estas abriendo el archivo en local, usa un servidor web ' +
      '(en GitHub Pages funciona directamente).</div>';
  }
}
