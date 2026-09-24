// Rellena la portada con lo que hay ahora mismo en cada seccion: cuando se
// actualizo, su noticia numero 1 y cuanto trae. Lee los mismos JSON que pinta
// cada seccion, asi que esto no obliga a las rutinas a escribir nada nuevo.
//
// Si un JSON no carga, su entrada se queda con el texto que trae escrito en el
// HTML, que es la descripcion que tenia la portada de siempre: por un fetch que
// falle, la portada nunca puede quedarse peor que antes.
//
// El orden de las entradas es el del HTML y no el de la hora de actualizacion.
// Ordenarlas por lo mas reciente las cambiaria de sitio dos veces al dia, y una
// portada que se reordena sola obliga a leerla entera para encontrar lo de
// siempre.
//
// La marca "nuevo" compara el campo 'actualizado' con el que se guardo la
// ultima vez que se abrio esa seccion (lo escribe assets/noticias.js al
// pintarla). Ofertas no la lleva a proposito: su JSON se reescribe dos veces al
// dia hayan cambiado los precios o no, asi que ahi la marca saldria siempre, y
// un aviso que sale siempre es un aviso que se deja de leer.

// La misma clave que escribe assets/noticias.js. Si se cambia, cambiarla ahi.
const CLAVE_VISTO = 'visto:';

// El navegador puede tener el almacenamiento capado (ventana privada, ajustes
// del movil) y ahi leerlo lanza. Sin esto, la portada entera se caeria por
// consultar una marca que es lo menos importante de la pagina.
function visto(seccion) {
  try {
    return localStorage.getItem(CLAVE_VISTO + seccion);
  } catch (e) {
    return null;
  }
}

// "21-08-2026 04:09" -> "hoy 04:09". Con la fecha entera delante hay que restar
// mentalmente en cada entrada para saber si eso es de hoy, que es justo lo que
// se viene a mirar.
function cuando(actualizado) {
  const partes = /^(\d{2})-(\d{2})-(\d{4})(?:\s+(\d{2}):(\d{2}))?$/.exec(actualizado || '');
  if (!partes) return actualizado || '';

  const [, dia, mes, ano, hh, mm] = partes;
  const fecha = new Date(`${ano}-${mes}-${dia}T00:00:00`);
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);

  const dias = Math.round((hoy - fecha) / 86400000);
  const hora = hh ? ` ${hh}:${mm}` : '';

  if (dias === 0) return 'hoy' + hora;
  if (dias === 1) return 'ayer' + hora;
  return `${dia}-${mes}` + hora;
}

function contar(cuantos, singular, plural) {
  return `${cuantos} ${cuantos === 1 ? singular : plural}`;
}

// Con espacio que no se parte: en el movil el titular de Ofertas partia la
// linea entre la cifra y el simbolo, y "39,95" quedaba al final de una linea y
// el "€" al principio de la siguiente.
function euros(valor, moneda) {
  return Number(valor).toFixed(2).replace('.', ',') +
    '\u00a0' + (moneda === 'EUR' || !moneda ? '€' : moneda);
}

function deNoticias(datos) {
  // "noticias" es el formato antiguo, aceptado aqui por lo mismo que en
  // assets/noticias.js: que un cambio de formato no deje la web en blanco.
  const destacadas = Array.isArray(datos.destacadas) ? datos.destacadas
    : Array.isArray(datos.noticias) ? datos.noticias : [];
  const titulares = Array.isArray(datos.titulares) ? datos.titulares : [];
  const total = destacadas.length + titulares.length;
  const primera = destacadas[0] || titulares[0];

  return {
    titulo: primera ? primera.titulo : 'Todavia no hay noticias de hoy.',
    // Sin el recuento cuando no hay nada: el "sin noticias" ya lo dice el
    // titulo, y decirlo dos veces en la misma caja es ruido.
    cuando: '· ' + cuando(datos.actualizado) +
      (total ? ' · ' + contar(total, 'noticia', 'noticias') : ''),
    hayAlgo: total > 0,
  };
}

// Lo que se viene a preguntar aqui no es que es lo mas barato sino QUE ESTA A
// PUNTO DE CAER. Coronar el precio mas bajo daba siempre el juego mas barato
// del catalogo, que no dice nada: el 22-09-2026 salia Octopath a 28,95 EUR
// llevando catorce dias igual y con su objetivo a un 45% de distancia.
//
// Los ya cumplidos no entran: esos suben a la banda de avisos, arriba y en
// verde, asi que aqui solo se gastaria la entrada en repetirlos.
function deOfertas(datos) {
  const productos = Array.isArray(datos.productos) ? datos.productos : [];
  const metas = metasDeOfertas(datos);
  const cerca = masCerca(metas);

  // Los tres finales se distinguen porque quieren decir cosas distintas: no es
  // lo mismo que las tiendas no hayan respondido -que es una averia- que tener
  // todos los objetivos cumplidos, que es la mejor noticia posible.
  let titulo;
  if (cerca) {
    titulo = textoMeta(cerca);
  } else if (metas.length) {
    titulo = 'Todos tus precios objetivo estan cumplidos.';
  } else {
    titulo = 'Hoy no ha respondido ninguna tienda.';
  }

  return {
    titulo,
    cuando: '· ' + cuando(datos.actualizado) +
      ' · ' + contar(productos.length, 'juego', 'juegos'),
    hayAlgo: cerca != null,
  };
}

// Todos los sitios donde se puede comprar hoy un juego de la seccion: Steam
// -su edicion estandar- y las demas tiendas que trae ITAD.
//
// Es el mismo criterio que usa assets/steam.js dentro de la seccion, y esta
// escrito aparte a proposito: la portada no carga ofertas.js ni steam.js,
// que son seiscientas lineas para dos cuentas, y es la pagina que mas se abre.
// Si el criterio cambia alli, hay que mirarlo aqui.
//
// Solo entra lo de hoy, igual que en Ofertas: un precio marcado como viejo no
// se corona contra uno recien traido, porque esa comparacion no la ha hecho
// nadie.
function sitiosDeSteam(juego) {
  const sitios = [];
  const estandar = (juego.ediciones || [])[0];
  if (estandar && estandar.estado === 'ok' && estandar.precio != null) {
    sitios.push({ donde: 'Steam', precio: estandar.precio,
                  descuento: estandar.descuento || 0,
                  moneda: estandar.moneda });
  }
  for (const oferta of juego.tiendas || []) {
    if (oferta.precio == null) continue;
    sitios.push({ donde: oferta.tienda, precio: oferta.precio,
                  descuento: oferta.descuento || 0, moneda: 'EUR' });
  }
  return sitios;
}

// El resumen es el que esta mas cerca de su precio, igual que en Ofertas y por
// el mismo motivo: coronar la mayor rebaja daba siempre el juego mas barato de
// los 52 (el 22-09-2026, Blasphemous a 5,31 EUR al -79%), y un -79% no dice si
// eso esta cerca o lejos de lo que pagarias por el.
//
// La cuenta de la derecha sigue siendo la de rebajados, que ahi si informa: es
// cuanto se ha movido la seccion hoy.
function deSteam(datos) {
  const juegos = Array.isArray(datos.juegos) ? datos.juegos : [];
  const cerca = masCerca(metasDeSteam(datos));

  let rebajados = 0;
  for (const juego of juegos) {
    const sitios = sitiosDeSteam(juego);
    if (sitios.length && sitios.some((s) => s.descuento)) rebajados++;
  }

  return {
    titulo: cerca ? textoMeta(cerca)
                  : 'Ningun juego pendiente de llegar a tu precio.',
    cuando: '· ' + cuando(datos.actualizado) +
      ' · ' + (rebajados ? contar(rebajados, 'rebajado', 'rebajados')
                         : contar(juegos.length, 'juego', 'juegos')),
    hayAlgo: cerca != null,
  };
}

// -- Precios objetivo -----------------------------------------------------
//
// Una "meta" es un objetivo del usuario junto al precio con el que hay que
// compararlo. Se saca una sola vez y la usan las DOS cosas que hablan de
// objetivos en la portada: el aviso del que ya ha llegado y el resumen del que
// esta mas cerca. Calcularlo por separado en cada una es como acabarian
// diciendo cosas distintas del mismo juego el dia que se toque una y no la
// otra, que es lo mismo que ya evita que tecnologia apunte a la lista de IA en
// vez de repetirla.
function meta(cual, sitio, objetivo) {
  const falta = sitio.precio - objetivo;
  return {
    cual, objetivo,
    precio: sitio.precio,
    moneda: sitio.moneda,
    donde: sitio.donde,
    falta,
    // Lo que falta EN PROPORCION a lo que se pide, no en euros. En euros
    // ganaria siempre el juego barato: a uno de 5 EUR con objetivo 3 le faltan
    // 2, y a uno de 60 con objetivo 50 le faltan 10, aunque el segundo este
    // mucho mas cerca de cumplirse. Medido el 22-09-2026 sobre los datos del
    // dia: por euros la entrada de Steam corona NEEDY GIRL OVERDOSE (1,51) y
    // por proporcion SteamWorld Heist II, que esta al 50% de su meta.
    //
    // Un objetivo de 0 no se puede dividir; no lo hay, pero si lo hubiera se
    // compara por euros y no se cae la portada entera.
    cerca: objetivo > 0 ? falta / objetivo : falta,
  };
}

// La meta pendiente que menos le falta. Las cumplidas se quedan fuera porque
// esas ya suben solas como aviso, arriba y en verde: repetirlas aqui gastaria
// la entrada en decir dos veces lo mismo.
function masCerca(metas) {
  const pendientes = metas.filter((m) => m.falta > 0);
  if (!pendientes.length) return null;
  return pendientes.reduce((a, b) => (b.cerca < a.cerca ? b : a));
}

// Como se lee una meta en la entrada de la seccion. El "te faltan" es el mismo
// que pinta cada seccion al lado de su precio, para que el numero de la portada
// y el de dentro sean reconociblemente el mismo.
function textoMeta(m) {
  const donde = m.donde && m.donde !== 'Steam' ? ` en ${m.donde}` : '';
  return `Mas cerca de tu precio: ${m.cual}, ${euros(m.precio, m.moneda)}${donde}` +
         ` (te faltan ${euros(m.falta, m.moneda)})`;
}

function metasDeOfertas(datos) {
  const metas = [];
  for (const producto of datos.productos || []) {
    if (producto.objetivo == null) continue;
    const deHoy = (producto.precios || []).filter(
      (p) => p.estado === 'ok' && p.precio != null);
    if (!deHoy.length) continue;
    const barato = deHoy.reduce((a, b) => (b.precio < a.precio ? b : a));
    metas.push(meta(producto.nombre,
                    { precio: barato.precio, moneda: barato.moneda,
                      donde: barato.tienda },
                    producto.objetivo));
  }
  return metas;
}

// Aqui entran TODAS las ediciones con objetivo, bundles incluidos: un objetivo
// puesto sobre la Ultimate de Cyberpunk es una meta tan legitima como la del
// juego suelto. Es lo contrario de lo que hace el resumen de rebajas, que mira
// solo la estandar, y no es una incoherencia: una Deluxe al -70% sigue costando
// mas que la normal y coronarla seria vender como chollo el producto caro, pero
// una Deluxe a 12 EUR de SU precio esta a 12 EUR de su precio.
function metasDeSteam(datos) {
  const metas = [];
  for (const juego of datos.juegos || []) {
    (juego.ediciones || []).forEach((edicion, i) => {
      if (edicion.objetivo == null) return;

      // La estandar se compara contra el precio mas bajo de hoy en CUALQUIER
      // sitio: las demas tiendas venden ese mismo juego, asi que si ha llegado
      // a tu precio en Fanatical, ha llegado.
      //
      // Las ediciones especiales siguen mirando solo a Steam, y no es un
      // descuido: ITAD da el precio del JUEGO, no el de su Deluxe, asi que
      // Steam es el unico sitio donde se sabe que lo que vale eso es
      // exactamente esa edicion.
      let sitio;
      if (i === 0) {
        const sitios = sitiosDeSteam(juego);
        if (!sitios.length) return;
        sitio = sitios.reduce((a, b) => (b.precio < a.precio ? b : a));
      } else {
        if (edicion.estado !== 'ok' || edicion.precio == null) return;
        sitio = { donde: 'Steam', precio: edicion.precio, moneda: edicion.moneda };
      }

      // El nombre de la edicion solo se dice cuando no es la estandar: "Elden
      // Ring Estandar" suena a que hay algo que elegir donde no lo hay.
      const cual = i === 0 ? juego.nombre : `${juego.nombre} (${edicion.nombre})`;
      metas.push(meta(cual, sitio, edicion.objetivo));
    });
  }
  return metas;
}

// -- Avisos de precio -----------------------------------------------------
//
// Dos cosas merecen sacar al usuario de la portada, y ninguna pasa a menudo:
// que un juego llegue al precio al que interesa comprarlo, y que baje en
// Orange, donde hay ventajas por comprar. El resto de bajadas se ven dentro de
// la seccion: subirlas aqui llenaria la portada de avisos todos los dias y
// acabaria por no leerse ninguno.
const TIENDA_VIGILADA = 'Orange';

function avisosDeOfertas(datos) {
  const avisos = [];

  for (const m of metasDeOfertas(datos)) {
    if (m.falta > 0) continue;
    avisos.push({
      clase: 'cumplido ofe',
      icono: '€',
      texto: `${m.cual} esta a ${euros(m.precio, m.moneda)} en ${m.donde}: ` +
             'ha llegado a tu precio.',
    });
  }

  for (const producto of datos.productos || []) {
    const deHoy = (producto.precios || []).filter(
      (p) => p.estado === 'ok' && p.precio != null);
    if (!deHoy.length) continue;

    const vigilada = deHoy.find((p) => p.tienda === TIENDA_VIGILADA && p.bajada);
    if (vigilada && vigilada.bajada.desde > vigilada.precio) {
      avisos.push({
        clase: 'bajada ofe',
        icono: '↓',
        texto: `${producto.nombre} ha bajado en ${TIENDA_VIGILADA} a ` +
               `${euros(vigilada.precio, vigilada.moneda)}, desde ` +
               `${euros(vigilada.bajada.desde, vigilada.moneda)}.`,
      });
    }
  }

  return avisos;
}

// Los avisos de Steam: un juego, o una edicion suya, que llega al precio al
// que interesa comprarlo. Solo eso. Las rebajas normales se quedan dentro de
// la seccion con su etiqueta, porque el dia que se monto esto habia 18 juegos
// rebajados de 50 y un aviso por rebaja llenaria la portada a diario.
//
// Que merezca la pena subirlo aqui esta medido igual que en Ofertas: de los 43
// objetivos, el dia que se pusieron no habia ni uno cumplido, y al mas cercano
// le faltaba 1,51 EUR. Este aviso no va a salir casi nunca, que es la condicion
// para que se lea el dia que salga.
function avisosDeSteam(datos) {
  return metasDeSteam(datos)
    .filter((m) => m.falta <= 0)
    .map((m) => ({
      clase: 'cumplido ste',
      icono: '€',
      destino: 'steam.html',
      texto: `${m.cual} esta a ${euros(m.precio, m.moneda)} en ${m.donde}: ` +
             'ha llegado a tu precio.',
    }));
}

// Recibe ya la lista y no el JSON de una seccion: Ofertas y Steam avisan las
// dos, y como la portada las carga en paralelo, cada una pintando por su cuenta
// borraria a la otra con su innerHTML.
function pintarAvisos(avisos) {
  const caja = document.getElementById('avisos');
  if (!caja) return;
  if (!avisos.length) return;   // vacio se queda sin ocupar sitio

  caja.innerHTML = avisos.map((aviso) => `
    <a class="aviso-precio ${aviso.clase}" href="${aviso.destino || 'ofertas.html'}">
      <span class="aviso-icono" aria-hidden="true">${aviso.icono}</span>
      <span class="aviso-texto"></span>
    </a>`).join('');

  // El texto lleva nombres de producto que vienen de un JSON: se escribe como
  // texto y no como HTML, igual que en el resto de la web.
  caja.querySelectorAll('.aviso-texto').forEach((nodo, i) => {
    nodo.textContent = avisos[i].texto;
  });
}


// El aviso de que la web puede no estar al dia. Lo escribe 'noticias.py
// vigilar' en data/vigilancia.json desde una rutina de Claude, que corre fuera
// de GitHub y por eso puede avisar cuando lo que ha fallado es el propio cron
// de GitHub. Casi siempre esta vacio, como los de precio.
//
// Se pinta 'avisos' y NO 'disparos', y eso no es un olvido: son las dos listas
// que escribe 'vigilar'. Un disparo es un fallo que el push de ese mismo
// fichero esta arreglando (falta la pasada de precios -> el push lanza
// precios.yml), asi que para cuando alguien abra la portada ya no sera verdad.
// El 30-08-2026 se vio pintado: la banda decia que faltaban precios justo
// encima de una entrada de Ofertas que decia "hoy 09:40". Lo que sube aqui es
// lo que sigue roto, no lo que se esta reparando; si el disparo no sirve, la
// vigilancia siguiente lo mueve a 'avisos' y entonces si sale.
async function pintarVigilancia() {
  const caja = document.getElementById('avisos');
  if (!caja) return;

  let datos;
  try {
    const resp = await fetch('data/vigilancia.json?v=' + Date.now());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    datos = await resp.json();
  } catch (e) {
    return;  // sin fichero no hay aviso, que es el caso normal
  }

  const avisos = datos.avisos || [];
  if (!avisos.length) return;

  // Un solo bloque con todo, y delante de los avisos de precio: este dice que
  // lo de debajo puede no ser de hoy, asi que leerlo despues no sirve de nada.
  caja.insertAdjacentHTML('afterbegin', `
    <div class="aviso-precio aviso-vigilancia">
      <span class="aviso-icono" aria-hidden="true">!</span>
      <span>
        <span class="aviso-texto"></span>
        <span class="aviso-cuando"></span>
      </span>
    </div>`);

  const nodo = caja.querySelector('.aviso-vigilancia');
  // textContent y no HTML, igual que en el resto de la web: esto sale de un
  // JSON que escribe un script.
  nodo.querySelector('.aviso-texto').textContent =
    avisos.map((a) => a.texto).join(' ');
  nodo.querySelector('.aviso-cuando').textContent =
    'Comprobado el ' + (datos.comprobado || '?');
}


// -- La cabecera: el dia y el nido -------------------------------------------

// El dia de quien mira, no el de la ultima actualizacion: lo que se pregunta
// al abrir la portada es que hay de nuevo HOY, y la hora de cada seccion ya va
// en su entrada.
function pintarHoy() {
  const dia = document.getElementById('hoy-dia');
  const fecha = document.getElementById('hoy-fecha');
  if (!dia || !fecha) return;
  const hoy = new Date();
  const semana = hoy.toLocaleDateString('es-ES', { weekday: 'long' });
  dia.textContent = semana.charAt(0).toUpperCase() + semana.slice(1);
  fecha.textContent = hoy.toLocaleDateString('es-ES', { day: 'numeric', month: 'long' });
}

// Un huevo por entrada, en su orden y con su color, lleno si la entrada ha
// apuntado novedad. Sale de las entradas y no de una lista propia, asi que una
// seccion nueva aparece aqui sola en cuanto tiene su entrada.
function pintarNido(entradas) {
  const nido = document.getElementById('nido');
  if (!nido || !entradas.length) return;

  let llenos = 0;
  const huevos = Array.from(entradas, (entrada) => {
    const lleno = entrada.dataset.novedad === '1';
    if (lleno) llenos++;
    const acento = Array.from(entrada.classList)
      .filter((c) => c !== 'entrada' && c !== 'vacia').join(' ');
    // El nombre es el primer texto de la linea de la seccion: "Tecnologia".
    const linea = entrada.querySelector('.entrada-seccion');
    const nombre = (linea && linea.firstChild ? linea.firstChild.textContent : '').trim()
      || entrada.dataset.id;
    const estado = lleno ? 'hay novedades' : 'nada nuevo';
    return `<a class="${acento}${lleno ? ' lleno' : ''}" href="${entrada.getAttribute('href')}"
              title="${nombre}: ${estado}" aria-label="${nombre}: ${estado}">
              <span class="huevo" aria-hidden="true"></span></a>`;
  });

  nido.innerHTML = `
    <div class="nido-huevos">${huevos.join('')}</div>
    <p>${llenos ? `${llenos} de ${entradas.length} con novedades`
                : 'Nada nuevo desde tu ultima visita'}</p>`;
  nido.hidden = false;
}

async function cargarPortada() {
  const entradas = document.querySelectorAll('.entrada[data-json]');
  // Se juntan y se pintan al final, por lo que dice pintarAvisos: dos secciones
  // avisan y se cargan a la vez.
  const avisos = [];

  await Promise.all(Array.from(entradas, async (entrada) => {
    let datos;
    try {
      const resp = await fetch(entrada.dataset.json + '?v=' + Date.now());
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      datos = await resp.json();
    } catch (e) {
      return;  // la entrada se queda con lo que trae escrito
    }

    // Las dos secciones de precio avisan, y las dos solo por lo mismo: algo
    // que ha llegado al precio al que interesa comprarlo. Las rebajas normales
    // se quedan dentro de su seccion.
    const tipo = entrada.dataset.tipo;
    const suyos = tipo === 'ofertas' ? avisosDeOfertas(datos)
      : tipo === 'steam' ? avisosDeSteam(datos) : [];
    avisos.push(...suyos);
    // Para el nido. En las de precio la novedad es un aviso: la marca "nuevo"
    // no la llevan, por lo que dice arriba.
    if (suyos.length) entrada.dataset.novedad = '1';

    const resumen = tipo === 'ofertas' ? deOfertas(datos)
      : tipo === 'steam' ? deSteam(datos)
      : deNoticias(datos);

    const titulo = entrada.querySelector('.entrada-titulo');
    if (titulo) titulo.textContent = resumen.titulo;

    const desde = entrada.querySelector('.entrada-cuando');
    if (desde) desde.textContent = resumen.cuando;

    entrada.classList.toggle('vacia', !resumen.hayAlgo);

    const marca = entrada.querySelector('.nuevo');
    if (marca && resumen.hayAlgo && datos.actualizado !== visto(entrada.dataset.id)) {
      marca.hidden = false;
      entrada.dataset.novedad = '1';
    }
  }));

  pintarAvisos(avisos);
  pintarNido(entradas);
}

pintarHoy();
cargarPortada().then(pintarVigilancia);
