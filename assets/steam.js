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

// -- Las otras tiendas ----------------------------------------------------
//
// Aqui las filas SI compiten, justo al reves que las ediciones de arriba: son
// el mismo juego en sitios distintos y la pregunta es donde sale mas barato.
// Por eso estas llevan el "Mas barato" y el "+X,XX" que aquellas no llevan.
//
// No se reutiliza pintarPrecio() de ofertas.js aunque lo pareciera de lejos:
// sus filas no tienen plataforma, ni cupon, ni tarifa tachada, y meter esos
// tres casos alli obligaria a que Ofertas supiera de Steam. Lo que si se
// reutiliza, que es lo que hace que las dos secciones se vean iguales, son las
// clases del CSS y el formateo de precios.

const MARCAS_ITAD = {
  H: 'Minimo historico',
  N: 'NUEVO minimo historico',
  S: 'Minimo en esta tienda',
};

// "2026-09-27T19:00:00+02:00" -> "27-09"
function finDeOferta(iso) {
  const t = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
  return t ? `${t[3]}-${t[2]}` : '';
}

function pintarTiendaSteam(oferta, barato) {
  const nombre = oferta.enlace
    ? `<a href="${escaparOferta(oferta.enlace)}" target="_blank" rel="noopener">${
        escaparOferta(oferta.tienda)}</a>`
    : escaparOferta(oferta.tienda);

  const etiquetas = [];
  if (oferta.descuento) {
    etiquetas.push(`<span class="etiqueta baja">-${oferta.descuento}%</span>`);
  }
  // La plataforma solo se dice cuando NO es Steam. De las 252 ofertas que hay
  // hoy, 239 son claves de Steam: una etiqueta que sale en casi todas las filas
  // no informa y tapa a las que si dicen algo. Cuando no viene declarada es la
  // nativa de esa tienda, y para eso ya esta el nombre de la tienda.
  if (oferta.plataforma && oferta.plataforma !== 'Steam') {
    etiquetas.push(`<span class="etiqueta">Para ${
      escaparOferta(oferta.plataforma)}</span>`);
  }
  // El precio de al lado YA lleva el cupon descontado, asi que esto no avisa de
  // una condicion escondida: dice el codigo que hay que escribir en la cesta
  // para pagar eso. Sin decirlo, el precio parece sencillamente mal.
  if (oferta.cupon) {
    etiquetas.push(`<span class="etiqueta estimado">Con el codigo ${
      escaparOferta(oferta.cupon)}</span>`);
  }
  // Del minimo solo se dice cuando el precio de hoy YA lo es, que es lo que
  // significan las marcas de ITAD. Lo contrario -"aqui se vio a 5,25"- se
  // probo y se quito: salia en 191 de las 252 filas, y con las marcas encima
  // eran las 252, o sea TODAS. No es que fuera falso, es que ITAD guarda anos
  // de historial y la mediana de esas rebajas pasadas es del 58%: cualquier
  // tienda ha tenido cualquier juego mucho mas barato alguna vez.
  //
  // Es la misma leccion que ya esta escrita en ofertas.js, donde el minimo
  // salia en 18 de 24 filas: lo que aparece en todas partes no informa, y
  // encima tapa a la fila que si tenia algo que contar. Aqui las que lo tienen
  // son estas, el 24%.
  //
  // Lo que se pierde -cuanto ha llegado a costar el juego- es una pregunta del
  // JUEGO y no de cada tienda, asi que su sitio es el bloque entero y no la
  // fila. Para eso esta 'minimo_itad', que ya se publica en el JSON.
  if (MARCAS_ITAD[oferta.marca]) {
    etiquetas.push(`<span class="etiqueta minimo">${
      MARCAS_ITAD[oferta.marca]}</span>`);
  }
  const fin = finDeOferta(oferta.caduca);
  if (fin) {
    etiquetas.push(`<span class="etiqueta">Termina el ${fin}</span>`);
  }

  // El empate es normal -media lista a 59,99- asi que puede haber varias filas
  // marcadas a la vez. Es correcto: dice que da igual cual elijas.
  const esBarato = barato != null && oferta.precio <= barato + 0.001;
  const diferencia = esBarato
    ? '<span class="marca-barato">Mas barato</span>'
    : (barato != null
        ? `<span class="diferencia">+${
            formatearPrecio(oferta.precio - barato)}</span>`
        : '');

  const antes = (oferta.base != null && oferta.base > oferta.precio)
    ? `<span class="antes">${formatearPrecio(oferta.base)}</span>` : '';

  return `
    <li class="precio${esBarato ? ' destacado' : ''}">
      <span class="tienda">${nombre}</span>
      ${diferencia}
      <span class="importes">${antes}<span class="importe">${
        formatearPrecio(oferta.precio)}</span></span>
      ${etiquetas.length ? `<span class="detalles">${etiquetas.join('')}</span>` : ''}
    </li>`;
}

// El precio mas bajo de HOY entre Steam y las demas tiendas.
//
// Es el cambio de fondo de la seccion: la cabecera ya no contesta "cuanto
// cuesta en Steam" sino "cuanto cuesta y donde", que es a lo que se entra. Por
// eso devuelve tambien el sitio: un numero mas bajo sin decir de donde sale
// obligaria a abrir el bloque para saber si se puede comprar ahi.
//
// Solo compite lo de hoy, igual que en Ofertas: un precio de Steam marcado como
// 'viejo' no puede coronarse contra uno recien traido, porque esa comparacion
// no la ha hecho nadie.
function mejorDeHoy(juego) {
  const estandar = (juego.ediciones || [])[0];
  const candidatos = [];
  if (estandar && estandar.precio != null && estandar.estado === 'ok') {
    candidatos.push({ precio: estandar.precio, donde: 'Steam',
                      descuento: estandar.descuento || 0,
                      moneda: estandar.moneda });
  }
  for (const oferta of juego.tiendas || []) {
    if (oferta.precio == null) continue;
    candidatos.push({ precio: oferta.precio, donde: oferta.tienda,
                      descuento: oferta.descuento || 0, moneda: 'EUR' });
  }
  if (!candidatos.length) return null;
  return candidatos.reduce((a, b) => (b.precio < a.precio ? b : a));
}

// El mayor descuento del juego en CUALQUIER sitio, que es por lo que se ordena
// la lista. Desde que hay otras tiendas, mirar solo el de Steam mandaba al
// fondo un juego al -70% en Fanatical y a 0% en Steam, que es justo el que se
// viene a ver.
function descuentoMayor(juego) {
  const estandar = (juego.ediciones || [])[0] || {};
  let mejor = estandar.estado === 'ok' ? (estandar.descuento || 0) : 0;
  for (const oferta of juego.tiendas || []) {
    if ((oferta.descuento || 0) > mejor) mejor = oferta.descuento || 0;
  }
  return mejor;
}

function pintarJuego(juego, series) {
  const ediciones = Array.isArray(juego.ediciones) ? juego.ediciones : [];
  const tiendas = Array.isArray(juego.tiendas) ? juego.tiendas : [];
  const estandar = ediciones[0];
  const filas = ediciones.length
    ? ediciones.map((e, i) => pintarEdicionSteam(e, i === 0)).join('')
    : '<li class="precio"><span class="importe sin-dato">Sin precios todavia</span></li>';

  // Plegado se ve el precio mas bajo de hoy, que es a lo que se entra. Con
  // 50 juegos, desplegar las ediciones de todos obligaria a hacer scroll para
  // comparar dos juegos entre si, que es lo primero que se mira.
  const mejor = mejorDeHoy(juego);
  let cabecera;
  if (mejor) {
    const donde = mejor.donde !== 'Steam'
      ? `<span class="cab-nota">en ${escaparOferta(mejor.donde)}</span>` : '';
    const rebaja = mejor.descuento
      ? `<span class="rebaja cab-rebaja">-${mejor.descuento}%</span>` : '';
    cabecera = `${donde}<span class="cab-precio">${
      formatearPrecio(mejor.precio, mejor.moneda)}</span>${rebaja}`;
  } else if (estandar && estandar.precio != null) {
    // Nada fresco en ningun sitio: se cae al ultimo precio conocido de Steam y
    // se dice, que es la regla de siempre para el sitio mas visible de la fila.
    const rebaja = estandar.descuento
      ? `<span class="rebaja cab-rebaja">-${estandar.descuento}%</span>` : '';
    cabecera = `<span class="cab-nota">no es de hoy</span><span class="cab-precio">${
      formatearPrecio(estandar.precio, estandar.moneda)}</span>${rebaja}`;
  } else {
    const porque = estandar && estandar.estado === 'proximamente' ? 'Proximamente'
      : estandar && estandar.estado === 'retirado' ? 'Ya no se vende'
      : 'Sin precio';
    cabecera = `<span class="cab-precio sin-dato">${porque}</span>`;
  }

  // Que hay ahi dentro, dicho en el titulo: plegado no se ve nada, y sin esto
  // no habria forma de saber que hay mas que un precio.
  const otras = ediciones.length - 1;
  const trozos = [];
  if (otras > 0) {
    trozos.push(`${otras} ${otras === 1 ? 'edicion especial' : 'ediciones especiales'}`);
  }
  if (tiendas.length) {
    trozos.push(`${tiendas.length} ${tiendas.length === 1 ? 'tienda' : 'tiendas'}`);
  }
  const cuantas = trozos.length
    ? `<span class="plataforma">${trozos.join(' · ')}</span>` : '';

  // En la cabecera va solo el objetivo de la estandar, que es el precio que se
  // ve plegado, y se compara contra el mas bajo de hoy y no contra el de Steam:
  // si el juego ha llegado a tu precio en Fanatical, ha llegado. Los objetivos
  // de las ediciones se leen al abrir, al lado del precio con el que hay que
  // compararlos.
  const meta = estandar
    ? pintarObjetivoSteam(estandar.objetivo,
                          mejor ? mejor.precio : estandar.precio,
                          estandar.moneda)
    : '';

  const grafico = pintarGrafico(
    ultimosDias(serieDelJuego(series, juego), DIAS_GRAFICO_STEAM),
    null, estandar ? estandar.moneda : 'EUR');

  const bloqueTiendas = tiendas.length ? `
      <div class="otras-tiendas">En otras tiendas</div>
      <ul class="lista-precios">${tiendas.map(
        (o) => pintarTiendaSteam(o, mejor ? mejor.precio : null)).join('')}</ul>`
    : '';

  return `
    <details class="producto">
      <summary class="producto-cab">
        <span class="producto-titulo">
          <span class="nombre">${juego.enlace
            ? `<a href="${escaparOferta(juego.enlace)}" target="_blank" rel="noopener">${
                escaparOferta(juego.nombre)}</a>`
            : escaparOferta(juego.nombre)}</span>
          ${cuantas}
          ${meta}
        </span>
        ${cabecera}
      </summary>
      ${grafico}
      <ul class="lista-precios">${filas}</ul>
      ${bloqueTiendas}
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
    const ordenados = juegos.slice().sort(
      (a, b) => descuentoMayor(b) - descuentoMayor(a));

    contenedor.innerHTML = ordenados.length
      ? ordenados.map((j) => pintarJuego(j, series)).join('')
      : '<div class="aviso">Todavia no hay juegos en seguimiento.</div>';

    // El titulo enlaza a Steam y vive dentro del <summary>, asi que sin esto un
    // clic en el nombre abriria la ficha Y plegaria el bloque a la vez. Se
    // delega en el contenedor y no se pone en cada enlace: hay 52 juegos y el
    // HTML se reescribe entero en cada carga.
    contenedor.addEventListener('click', (e) => {
      if (e.target.closest('.producto-cab a')) e.stopPropagation();
    });
  } catch (e) {
    fecha.textContent = '';
    contenedor.innerHTML =
      '<div class="aviso">No se ha podido cargar el contenido.<br>' +
      'Si estas abriendo el archivo en local, usa un servidor web ' +
      '(en GitHub Pages funciona directamente).</div>';
  }
}
