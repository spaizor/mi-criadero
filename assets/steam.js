// Carga data/steam.json y pinta un bloque por juego con el precio de su
// edicion estandar y, desplegadas, sus ediciones especiales.
//
// Se apoya en assets/ofertas.js, que steam.html carga antes: de alli salen
// escaparOferta, formatearPrecio y todo el dibujo del grafico. No se copian
// aqui porque dos copias de la misma funcion acaban siendo dos funciones
// distintas, que es lo mismo que ya evita que el bloque 'tema_ajeno' de
// tecnologia apunte a la lista de IA en vez de repetirla.
//
// Lo que NO se reutiliza es el reparto de la seccion, y esa es la diferencia
// de fondo entre las dos. En Ofertas las filas son tiendas y compiten: la
// pregunta es donde esta mas barato, y por eso hay un "Mas barato" y un
// "+9,00 EUR" contra el. Aqui las filas son ediciones del mismo juego y NO
// compiten: la Deluxe no es la estandar mas cara, es otro producto con mas
// cosas dentro. Coronar la estandar como la mas barata seria dar por hecha una
// comparacion que no significa nada.
//
// Un precio puede venir en cinco estados:
//   ok           -> consultado en esta pasada
//   viejo        -> la consulta fallo y se conserva el anterior, avisando
//   nuevo        -> juego recien anadido, todavia sin consultar
//   proximamente -> anunciado, pero sin fecha ni precio
//   retirado     -> ya salio, pero Steam ya no lo vende
//
// Los dos ultimos no son fallos, y por eso no se pintan como tales: la ficha
// de Steam los distingue sola y decirlo es mas util que un "sin precio" mudo.

const DIAS_GRAFICO_STEAM = 30;

// El precio al que interesa comprar. Se pinta SIEMPRE lo que falta y no solo
// al cruzarse, por lo mismo que en Ofertas: de los 43 objetivos del usuario
// ninguno estaba cumplido el dia que los puso, asi que una marca que apareciera
// solo al cumplirse no se veria en meses. La distancia dice algo cada dia.
//
// Va por edicion y no por juego porque cuatro de ellos son de la Deluxe o la
// Complete: una Deluxe a 22 EUR y un juego base a 22 EUR son metas distintas.
function pintarObjetivoSteam(objetivo, precio, moneda) {
  if (objetivo == null) return '';
  if (precio == null) {
    return `<span class="objetivo">Tu precio: ${formatearPrecio(objetivo, moneda)}</span>`;
  }
  if (precio <= objetivo) {
    return '<span class="objetivo cumplido">A tu precio</span>';
  }
  return `<span class="objetivo">Tu precio: ${formatearPrecio(objetivo, moneda)} · te faltan ${
    formatearPrecio(precio - objetivo, moneda)}</span>`;
}

function etiquetaEstado(edicion) {
  if (edicion.estado === 'viejo') {
    return '<span class="etiqueta viejo">No respondio: ultimo precio conocido</span>';
  }
  if (edicion.estado === 'proximamente') {
    return '<span class="etiqueta proximamente">Todavia no esta a la venta</span>';
  }
  if (edicion.estado === 'retirado') {
    return '<span class="etiqueta retirado">Steam ya no lo vende</span>';
  }
  if (edicion.estado === 'nuevo') {
    return '<span class="etiqueta">Recien anadido, sin consultar</span>';
  }
  return '';
}

function pintarEdicionSteam(edicion, esEstandar) {
  const nombre = edicion.enlace
    ? `<a href="${escaparOferta(edicion.enlace)}" target="_blank" rel="noopener">${
        escaparOferta(edicion.nombre)}</a>`
    : escaparOferta(edicion.nombre);

  const etiquetas = [];
  const estado = etiquetaEstado(edicion);
  if (estado) etiquetas.push(estado);

  if (edicion.bajada && edicion.bajada.desde > edicion.precio) {
    etiquetas.push(`<span class="etiqueta baja">Ha bajado desde ${
      formatearPrecio(edicion.bajada.desde, edicion.moneda)}</span>`);
  }
  // El minimo solo se ensena cuando dice algo. Si el precio de hoy ya es el
  // mas bajo que hemos visto, un "es el minimo" debajo de casi todas las filas
  // es ruido que tapa justo a las que si han estado mas baratas alguna vez.
  if (edicion.minimo != null && edicion.precio != null
      && edicion.minimo < edicion.precio) {
    etiquetas.push(`<span class="etiqueta minimo">Visto a ${
      formatearPrecio(edicion.minimo, edicion.moneda)}${
      edicion.minimo_fecha ? ' el ' + escaparOferta(edicion.minimo_fecha) : ''}</span>`);
  }

  // Los dos precios van envueltos en un solo elemento y no sueltos: la fila es
  // un grid de tres columnas (nombre, rebaja, importe) heredado de Ofertas, y
  // un cuarto hijo se desborda a la linea siguiente.
  let importe;
  if (edicion.precio == null) {
    importe = '<span class="importes"><span class="importe sin-dato">Sin precio</span></span>';
  } else {
    // El precio de antes solo se pinta si es distinto: sin descuento los dos
    // numeros son el mismo, y uno tachado al lado solo hace dudar.
    const antes = (edicion.base != null && edicion.base > edicion.precio)
      ? `<span class="antes">${formatearPrecio(edicion.base, edicion.moneda)}</span>`
      : '';
    importe = `<span class="importes">${antes}<span class="importe">${
      formatearPrecio(edicion.precio, edicion.moneda)}</span></span>`;
  }

  const meta = pintarObjetivoSteam(edicion.objetivo, edicion.precio, edicion.moneda);
  if (meta) etiquetas.unshift(meta);

  const rebaja = edicion.descuento
    ? `<span class="rebaja">-${edicion.descuento}%</span>`
    : '';

  return `
    <li class="precio${esEstandar ? '' : ' edicion'}">
      <span class="tienda">${nombre}</span>
      ${rebaja}
      ${importe}
      ${etiquetas.length ? `<span class="detalles">${etiquetas.join('')}</span>` : ''}
    </li>`;
}

// La serie que se dibuja es la de la edicion estandar, no la del conjunto.
// Mezclarlas daria una linea que salta de un producto a otro cada vez que sale
// una edicion nueva, y la pregunta a la que se viene es cuanto ha costado EL
// juego.
function serieDelJuego(series, juego) {
  const suyas = (series || {})[juego.id] || {};
  const estandar = suyas['Estandar'];
  return estandar ? serieDelMinimo({ Estandar: estandar }) : [];
}

function pintarJuego(juego, series) {
  const ediciones = Array.isArray(juego.ediciones) ? juego.ediciones : [];
  const estandar = ediciones[0];
  const filas = ediciones.length
    ? ediciones.map((e, i) => pintarEdicionSteam(e, i === 0)).join('')
    : '<li class="precio"><span class="importe sin-dato">Sin precios todavia</span></li>';

  // Plegado se ve el precio de la estandar, que es a lo que se entra. Con
  // 50 juegos, desplegar las ediciones de todos obligaria a hacer scroll para
  // comparar dos juegos entre si, que es lo primero que se mira.
  let cabecera;
  if (!estandar || estandar.precio == null) {
    const porque = estandar && estandar.estado === 'proximamente' ? 'Proximamente'
      : estandar && estandar.estado === 'retirado' ? 'Ya no se vende'
      : 'Sin precio';
    cabecera = `<span class="cab-precio sin-dato">${porque}</span>`;
  } else {
    const viejo = estandar.estado !== 'ok'
      ? '<span class="cab-nota">no es de hoy</span>' : '';
    const rebaja = estandar.descuento
      ? `<span class="rebaja cab-rebaja">-${estandar.descuento}%</span>` : '';
    cabecera = `${viejo}<span class="cab-precio">${
      formatearPrecio(estandar.precio, estandar.moneda)}</span>${rebaja}`;
  }

  // Cuantas ediciones hay, dicho en el titulo: plegado no se ven, y sin esto
  // no habria forma de saber que ahi dentro hay algo mas que un precio.
  const otras = ediciones.length - 1;
  const cuantas = otras > 0
    ? `<span class="plataforma">${otras} ${
        otras === 1 ? 'edicion especial' : 'ediciones especiales'}</span>`
    : '';

  // En la cabecera va solo el objetivo de la estandar, que es el precio que se
  // ve plegado. Los de las ediciones se leen al abrir, junto al precio con el
  // que hay que compararlos: subirlos aqui pondria dos metas distintas al lado
  // de un solo numero.
  const meta = estandar
    ? pintarObjetivoSteam(estandar.objetivo, estandar.precio, estandar.moneda)
    : '';

  const grafico = pintarGrafico(
    ultimosDias(serieDelJuego(series, juego), DIAS_GRAFICO_STEAM),
    null, estandar ? estandar.moneda : 'EUR');

  return `
    <details class="producto">
      <summary class="producto-cab">
        <span class="producto-titulo">
          <span class="nombre">${escaparOferta(juego.nombre)}</span>
          ${cuantas}
          ${meta}
        </span>
        ${cabecera}
      </summary>
      ${grafico}
      <ul class="lista-precios">${filas}</ul>
    </details>`;
}

// Los dos ultimos meses de serie: 30 dias pueden cruzar el cambio de mes.
function mesesDeSteam() {
  const hoy = new Date();
  return [1, 0].map((atras) => {
    const d = new Date(hoy.getFullYear(), hoy.getMonth() - atras, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
}

async function cargarSeriesSteam() {
  const partes = await Promise.all(mesesDeSteam().map(async (mes) => {
    try {
      const resp = await fetch(`data/steam-precios/${mes}.json?v=` + Date.now());
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return (await resp.json()).juegos || {};
    } catch (e) {
      // Sin serie no hay grafico, pero los precios de hoy se pintan igual:
      // esto es un extra y no puede tumbar la seccion.
      return {};
    }
  }));

  const juntas = {};
  for (const parte of partes) {
    for (const [juego, ediciones] of Object.entries(parte)) {
      const destino = juntas[juego] || (juntas[juego] = {});
      for (const [edicion, puntos] of Object.entries(ediciones)) {
        destino[edicion] = (destino[edicion] || []).concat(puntos);
      }
    }
  }
  return juntas;
}

async function cargarSteam(ruta) {
  const contenedor = document.getElementById('steam');
  const fecha = document.getElementById('fecha');

  try {
    const resp = await fetch(ruta + '?v=' + Date.now());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const datos = await resp.json();

    fecha.textContent = datos.actualizado
      ? 'Precios consultados: ' + datos.actualizado
      : '';

    const juegos = Array.isArray(datos.juegos) ? datos.juegos : [];
    const series = await cargarSeriesSteam();

    // Los rebajados primero: con 50 juegos, lo que se viene a ver es que ha
    // bajado hoy, y en orden alfabetico eso obliga a recorrer la lista entera.
    // Dentro de cada grupo se mantiene el orden del JSON, que es estable.
    const ordenados = juegos.slice().sort((a, b) => {
      const suyo = (j) => (j.ediciones || [])[0] || {};
      return (suyo(b).descuento || 0) - (suyo(a).descuento || 0);
    });

    contenedor.innerHTML = ordenados.length
      ? ordenados.map((j) => pintarJuego(j, series)).join('')
      : '<div class="aviso">Todavia no hay juegos en seguimiento.</div>';
  } catch (e) {
    fecha.textContent = '';
    contenedor.innerHTML =
      '<div class="aviso">No se ha podido cargar el contenido.<br>' +
      'Si estas abriendo el archivo en local, usa un servidor web ' +
      '(en GitHub Pages funciona directamente).</div>';
  }
}
