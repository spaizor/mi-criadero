// Carga data/ofertas.json y pinta un bloque por producto con el precio de cada
// tienda. Igual que en las noticias, el HTML no cambia nunca: el JSON lo
// reescribe scripts/precios.py en cada ejecucion.
//
// Un precio puede venir en cuatro estados:
//   ok     -> consultado en esta ejecucion
//   viejo  -> la tienda no respondio y se conserva el anterior, avisando
//   nuevo  -> producto recien anadido, todavia sin consultar
//   enlace -> tienda que solo responde desde casa: no se consulta, se deja el
//             enlace y el ultimo precio conocido con su fecha
//
// Solo 'ok' compite por ser el mas barato. Coronar un precio de hace dias
// frente a uno de hoy seria dar por buena una comparacion que no se ha hecho.

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
  const enlazado = p.enlace
    ? `<a href="${escaparOferta(p.enlace)}" target="_blank" rel="noopener">${escaparOferta(p.tienda)}</a>`
    : escaparOferta(p.tienda);

  if (p.precio == null) {
    // Sin precio conocido, la tienda sigue valiendo como enlace: el aviso
    // invita a mirarlo alli en vez de dejar la fila muerta.
    return `
      <li class="precio">
        <span class="tienda">${enlazado}</span>
        <span class="importe sin-dato">${
          p.estado === 'enlace' ? 'Ver en la tienda' : 'Sin consultar'}</span>
      </li>`;
  }

  const etiquetas = [];
  if (esMasBarato) etiquetas.push('<span class="etiqueta barato">Mas barato</span>');
  if (p.estado === 'viejo') {
    etiquetas.push('<span class="etiqueta viejo">No responde: ultimo precio conocido</span>');
  }
  if (p.estado === 'enlace') {
    etiquetas.push(`<span class="etiqueta enlace">No se consulta sola${
      p.consultado ? ': precio visto el ' + escaparOferta(p.consultado) : ''}</span>`);
  }
  if (p.disponible === false) {
    etiquetas.push('<span class="etiqueta agotado">Sin stock</span>');
  }
  // La tienda no publica el precio del producto sino la cuota de una
  // financiacion: el importe de al lado lo hemos reconstruido nosotros, y
  // decirlo es la diferencia entre un dato y una invencion.
  if (p.estimado) {
    etiquetas.push(`<span class="etiqueta estimado">Estimado: ${
      formatearPrecio(p.estimado.cuota, p.moneda)}/mes x ${
      p.estimado.meses} + IVA</span>`);
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

  return `
    <li class="precio${esMasBarato ? ' destacado' : ''}">
      <span class="tienda">${enlazado}</span>
      <span class="importe">${formatearPrecio(p.precio, p.moneda)}</span>
      <span class="detalles">${etiquetas.join('')}${minimo}</span>
    </li>`;
}

function pintarProducto(producto) {
  const precios = Array.isArray(producto.precios) ? producto.precios : [];
  const validos = precios.filter(p => p.precio != null && p.estado === 'ok');
  const barato = validos.length > 1
    ? Math.min(...validos.map(p => p.precio))
    : null;

  const filas = precios.length
    ? precios.map(p => pintarPrecio(
        p, barato != null && p.estado === 'ok' && p.precio === barato)).join('')
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
