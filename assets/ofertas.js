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
// Por lo mismo los 'ok' se pintan juntos y arriba: intercalar entre ellos un
// precio viejo lo haria parecer igual de comparable de un vistazo.

function escaparOferta(texto) {
  const d = document.createElement('div');
  d.textContent = texto == null ? '' : String(texto);
  return d.innerHTML;
}

function formatearPrecio(valor, moneda) {
  const numero = Number(valor).toFixed(2).replace('.', ',');
  return numero + ' ' + (moneda === 'EUR' || !moneda ? '€' : escaparOferta(moneda));
}

function pintarPrecio(p, barato) {
  const enlazado = p.enlace
    ? `<a href="${escaparOferta(p.enlace)}" target="_blank" rel="noopener">${escaparOferta(p.tienda)}</a>`
    : escaparOferta(p.tienda);

  const esMasBarato = barato != null && p.estado === 'ok' && p.precio === barato;

  const etiquetas = [];
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
  // Solo se enarbola el minimo cuando dice algo: si el precio de hoy YA es el
  // mas bajo que hemos visto, un "es el minimo" debajo de casi todas las filas
  // es ruido que tapa justo a las dos que si han bajado de precio alguna vez.
  if (p.minimo != null && p.minimo < p.precio) {
    etiquetas.push(`<span class="etiqueta minimo">Visto a ${
      formatearPrecio(p.minimo, p.moneda)}${
      p.minimo_fecha ? ' el ' + escaparOferta(p.minimo_fecha) : ''}</span>`);
  }

  // Cuanto cuesta de mas que el mas barato de hoy. Es la comparacion que se
  // venia a hacer, y en numero se lee sin restar de cabeza.
  let diferencia = '';
  if (esMasBarato) {
    diferencia = '<span class="marca-barato">Mas barato</span>';
  } else if (barato != null && p.estado === 'ok') {
    diferencia = `<span class="diferencia">+${formatearPrecio(p.precio - barato, p.moneda)}</span>`;
  }

  return `
    <li class="precio${esMasBarato ? ' destacado' : ''}">
      <span class="tienda">${enlazado}</span>
      ${diferencia}
      <span class="importe">${formatearPrecio(p.precio, p.moneda)}</span>
      ${etiquetas.length ? `<span class="detalles">${etiquetas.join('')}</span>` : ''}
    </li>`;
}

function pintarSinPrecio(p) {
  const enlazado = p.enlace
    ? `<a href="${escaparOferta(p.enlace)}" target="_blank" rel="noopener">${escaparOferta(p.tienda)}</a>`
    : escaparOferta(p.tienda);
  return `<li>${enlazado}</li>`;
}

// El precio que se ve con el producto plegado. Se prefiere el mas bajo de hoy;
// solo si ninguna tienda ha respondido se cae al mas bajo que se conserve, y
// entonces se dice, porque un precio de hace dias sin avisar en el sitio mas
// visible de la pagina es justo lo que evita que los 'viejo' no compitan por
// "Mas barato" ahi abajo.
function precioDeCabecera(conPrecio) {
  const deHoy = conPrecio.filter(p => p.estado === 'ok');
  const base = deHoy.length ? deHoy : conPrecio;
  if (!base.length) return null;
  const barato = base.reduce((a, b) => (b.precio < a.precio ? b : a));
  return { precio: barato.precio, moneda: barato.moneda, esDeHoy: deHoy.length > 0 };
}

function pintarProducto(producto) {
  const precios = Array.isArray(producto.precios) ? producto.precios : [];
  const conPrecio = precios.filter(p => p.precio != null);
  // Las tiendas sin precio no ocupan una fila entera cada una: juntas abajo
  // siguen a un clic, pero dejan de competir en tamano con los precios.
  const sinPrecio = precios.filter(p => p.precio == null);

  const validos = conPrecio.filter(p => p.estado === 'ok');
  const barato = validos.length > 1
    ? Math.min(...validos.map(p => p.precio))
    : null;

  // Los de hoy primero y de mas barato a mas caro; los viejos, detras.
  const ordenados = conPrecio.slice().sort((a, b) => {
    const fresco = (a.estado === 'ok' ? 0 : 1) - (b.estado === 'ok' ? 0 : 1);
    return fresco !== 0 ? fresco : a.precio - b.precio;
  });

  const filas = ordenados.length
    ? ordenados.map(p => pintarPrecio(p, barato)).join('')
    : '<li class="precio"><span class="importe sin-dato">Sin precios todavia</span></li>';

  const otras = sinPrecio.length
    ? `<div class="sin-precio">
         <span class="sin-precio-titulo">Tambien a la venta en</span>
         <ul>${sinPrecio.map(pintarSinPrecio).join('')}</ul>
       </div>`
    : '';

  const cabecera = precioDeCabecera(conPrecio);
  const importe = cabecera
    ? `${cabecera.esDeHoy ? '' : '<span class="cab-nota">no es de hoy</span>'}
       <span class="cab-precio">${formatearPrecio(cabecera.precio, cabecera.moneda)}</span>`
    : '<span class="cab-precio sin-dato">Sin precios</span>';

  // Un <details> y no un desplegable a mano: el navegador ya da el teclado, el
  // estado para los lectores de pantalla y la busqueda dentro de la pagina.
  // Plegado se ve solo el precio mas bajo, que es a lo que se entra; las
  // tiendas, que es la comparacion, estan a un clic.
  return `
    <details class="producto">
      <summary class="producto-cab">
        <span class="producto-titulo">
          <span class="nombre">${escaparOferta(producto.nombre)}</span>
          ${producto.plataforma
            ? `<span class="plataforma">${escaparOferta(producto.plataforma)}</span>`
            : ''}
        </span>
        ${importe}
      </summary>
      <ul class="lista-precios">${filas}</ul>
      ${otras}
    </details>`;
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
