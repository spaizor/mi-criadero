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
//
// Ademas de los precios de hoy se lee la serie de data/precios/AAAA-MM.json,
// que guarda un punto cada vez que un precio cambia. De ahi salen el grafico
// de 30 dias y el "de 50,90 a 59,99" que lo acompana.

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
  // Ha bajado desde la ultima vez que se miro. Es lo que se viene a ver, asi
  // que va en verde y no como una etiqueta gris mas.
  if (p.bajada && p.bajada.desde > p.precio) {
    etiquetas.push(`<span class="etiqueta baja">Ha bajado desde ${
      formatearPrecio(p.bajada.desde, p.moneda)}</span>`);
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

// -- La serie de precios --------------------------------------------------
//
// Cada tienda tiene sus propios puntos, uno por cambio de precio. Lo que se
// dibuja no es una linea por tienda -seis lineas en 40 px no se leen- sino la
// del precio mas bajo del producto en cada momento, que es la pregunta a la
// que se viene: cuanto ha costado esto.

const DIAS_GRAFICO = 30;

function aFecha(cuando) {
  // "10-08-2026 10:24" -> Date
  const t = /^(\d{2})-(\d{2})-(\d{4})(?:\s+(\d{2}):(\d{2}))?$/.exec(cuando || '');
  if (!t) return null;
  return new Date(`${t[3]}-${t[2]}-${t[1]}T${t[4] || '00'}:${t[5] || '00'}:00`);
}

function serieDelMinimo(porTienda) {
  const eventos = [];
  for (const [tienda, puntos] of Object.entries(porTienda || {})) {
    for (const punto of puntos) {
      const momento = aFecha(punto.cuando);
      if (momento) eventos.push({ t: +momento, tienda, precio: punto.precio });
    }
  }
  eventos.sort((a, b) => a.t - b.t);

  // Cada tienda mantiene su ultimo precio hasta que cambia: la serie es
  // escalonada por definicion, y por eso solo se guardan los cambios.
  // Los puntos del mismo instante entran TODOS antes de calcular el minimo.
  // Uno a uno, la primera pasada dibujaba un escalon que nunca existio: el
  // primer evento se compara consigo mismo, cuando todavia no se conocen las
  // demas tiendas. Super Mario RPG salia arrancando en 56,12 y cayendo a 39,99
  // en el mismo minuto, y esa caida no la vio nadie.
  const vigente = {};
  const linea = [];
  let i = 0;
  while (i < eventos.length) {
    const instante = eventos[i].t;
    while (i < eventos.length && eventos[i].t === instante) {
      vigente[eventos[i].tienda] = eventos[i].precio;
      i++;
    }
    linea.push({ t: instante, precio: Math.min(...Object.values(vigente)) });
  }
  return linea;
}

function ultimosDias(linea, dias) {
  const desde = Date.now() - dias * 86400000;
  const dentro = linea.filter((p) => p.t >= desde);
  const antes = linea.filter((p) => p.t < desde);

  // El precio que ya regia al empezar la ventana: sin esto el grafico
  // arrancaria en el primer cambio y pareceria que antes no habia precio.
  if (antes.length) dentro.unshift({ t: desde, precio: antes[antes.length - 1].precio });
  // Y se estira hasta hoy, porque el ultimo precio sigue vigente.
  if (dentro.length) dentro.push({ t: Date.now(), precio: dentro[dentro.length - 1].precio });
  return dentro;
}

function pintarGrafico(linea, objetivo, moneda) {
  if (linea.length < 2) return '';

  const ANCHO = 260, ALTO = 44, MARGEN = 4;
  const tiempos = linea.map((p) => p.t);
  const precios = linea.map((p) => p.precio);
  const t0 = Math.min(...tiempos), t1 = Math.max(...tiempos);
  const v0 = Math.min(...precios), v1 = Math.max(...precios);

  const x = (t) => MARGEN + (t1 === t0 ? 0 : (t - t0) / (t1 - t0)) * (ANCHO - 2 * MARGEN);
  // Precio alto arriba. Si nunca cambio, la linea va por el medio en vez de
  // pegarse a un borde por una division entre cero.
  const y = (v) => MARGEN + (v1 === v0 ? 0.5 : (v1 - v) / (v1 - v0)) * (ALTO - 2 * MARGEN);

  let trazo = `M ${x(linea[0].t)},${y(linea[0].precio)}`;
  for (let i = 1; i < linea.length; i++) {
    trazo += ` L ${x(linea[i].t)},${y(linea[i - 1].precio)}` +
             ` L ${x(linea[i].t)},${y(linea[i].precio)}`;
  }

  // El objetivo solo se dibuja si cae dentro de lo que ha valido. Con un
  // objetivo un 40% por debajo, meterlo en la escala aplastaria la linea
  // contra el techo y no se veria ningun movimiento.
  const meta = (objetivo != null && objetivo >= v0 && objetivo <= v1)
    ? `<line x1="${MARGEN}" y1="${y(objetivo)}" x2="${ANCHO - MARGEN}" y2="${y(objetivo)}"
             stroke="currentColor" stroke-width="1" stroke-dasharray="3 3" opacity="0.45"/>`
    : '';

  const resumen = v0 === v1
    ? `Sin cambios en ${DIAS_GRAFICO} dias`
    : `En ${DIAS_GRAFICO} dias: de ${formatearPrecio(v0, moneda)} a ${formatearPrecio(v1, moneda)}`;

  return `
    <div class="grafico">
      <svg viewBox="0 0 ${ANCHO} ${ALTO}" role="img"
           aria-label="${escaparOferta(resumen)}">
        ${meta}
        <path d="${trazo}" fill="none" stroke="currentColor" stroke-width="1.5"
              stroke-linejoin="round"/>
      </svg>
      <span class="grafico-pie">${escaparOferta(resumen)}</span>
    </div>`;
}

// -- El objetivo ----------------------------------------------------------
//
// Se pinta SIEMPRE lo que falta, no solo cuando se cruza. Ninguno de los
// objetivos se ha rozado en los primeros quince dias de datos, asi que una
// marca que solo apareciera al cumplirse no se veria en meses; la distancia,
// en cambio, dice algo cada dia.
function pintarObjetivo(objetivo, hoy, moneda) {
  if (objetivo == null) return '';
  if (hoy == null) {
    return `<span class="objetivo">Tu precio: ${formatearPrecio(objetivo, moneda)}</span>`;
  }
  if (hoy <= objetivo) {
    return '<span class="objetivo cumplido">A tu precio</span>';
  }
  const falta = hoy - objetivo;
  return `<span class="objetivo">Tu precio: ${formatearPrecio(objetivo, moneda)} · te faltan ${
    formatearPrecio(falta, moneda)}</span>`;
}


function pintarProducto(producto, series) {
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
  const moneda = (conPrecio[0] || {}).moneda;
  // Contra el precio de hoy, no contra el ultimo conocido: decir "te faltan
  // 9 EUR" con un precio de hace tres dias es prometer algo que no se sabe.
  const deHoy = validos.length ? Math.min(...validos.map((p) => p.precio)) : null;
  const objetivo = pintarObjetivo(producto.objetivo, deHoy, moneda);
  const grafico = pintarGrafico(
    ultimosDias(serieDelMinimo((series || {})[producto.id]), DIAS_GRAFICO),
    producto.objetivo, moneda);
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
          ${objetivo}
        </span>
        ${importe}
      </summary>
      ${grafico}
      <ul class="lista-precios">${filas}</ul>
      ${otras}
    </details>`;
}

// Los dos ultimos meses de serie: 30 dias pueden cruzar el cambio de mes.
// Son unos pocos KB, asi que se piden con la pagina y no al desplegar cada
// producto, que obligaria a repintar.
function mesesDelGrafico() {
  const hoy = new Date();
  return [1, 0].map((atras) => {
    const d = new Date(hoy.getFullYear(), hoy.getMonth() - atras, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
}

async function cargarSeries() {
  const partes = await Promise.all(mesesDelGrafico().map(async (mes) => {
    try {
      const resp = await fetch(`data/precios/${mes}.json?v=` + Date.now());
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return (await resp.json()).productos || {};
    } catch (e) {
      // Sin serie no hay grafico, pero los precios de hoy se pintan igual:
      // esto es un extra, no puede tumbar la seccion.
      return {};
    }
  }));

  const juntas = {};
  for (const parte of partes) {
    for (const [producto, tiendas] of Object.entries(parte)) {
      const destino = juntas[producto] || (juntas[producto] = {});
      for (const [tienda, puntos] of Object.entries(tiendas)) {
        destino[tienda] = (destino[tienda] || []).concat(puntos);
      }
    }
  }
  return juntas;
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
    const series = await cargarSeries();
    contenedor.innerHTML = productos.length
      ? productos.map((p) => pintarProducto(p, series)).join('')
      : '<div class="aviso">Todavia no hay productos en seguimiento.</div>';
  } catch (e) {
    fecha.textContent = '';
    contenedor.innerHTML =
      '<div class="aviso">No se ha podido cargar el contenido.<br>' +
      'Si estas abriendo el archivo en local, usa un servidor web ' +
      '(en GitHub Pages funciona directamente).</div>';
  }
}
