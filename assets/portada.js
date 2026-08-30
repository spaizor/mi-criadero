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

function euros(valor, moneda) {
  return Number(valor).toFixed(2).replace('.', ',') +
    ' ' + (moneda === 'EUR' || !moneda ? '€' : moneda);
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

function deOfertas(datos) {
  const productos = Array.isArray(datos.productos) ? datos.productos : [];

  // Solo los precios de hoy, por lo mismo que solo ellos compiten por "Mas
  // barato" dentro de la seccion: coronar en portada uno de hace dias seria
  // dar por hecha una comparacion que no se ha hecho.
  let barato = null;
  for (const producto of productos) {
    for (const precio of producto.precios || []) {
      if (precio.estado !== 'ok' || precio.precio == null) continue;
      if (!barato || precio.precio < barato.precio) {
        barato = { precio: precio.precio, moneda: precio.moneda, nombre: producto.nombre };
      }
    }
  }

  return {
    titulo: barato
      ? `Lo mas barato de hoy: ${barato.nombre}, ${euros(barato.precio, barato.moneda)}`
      : 'Hoy no ha respondido ninguna tienda.',
    cuando: '· ' + cuando(datos.actualizado) +
      ' · ' + contar(productos.length, 'juego', 'juegos'),
    hayAlgo: barato != null,
  };
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

  for (const producto of datos.productos || []) {
    const deHoy = (producto.precios || []).filter(
      (p) => p.estado === 'ok' && p.precio != null);
    if (!deHoy.length) continue;

    const barato = deHoy.reduce((a, b) => (b.precio < a.precio ? b : a));

    if (producto.objetivo != null && barato.precio <= producto.objetivo) {
      avisos.push({
        clase: 'cumplido',
        icono: '🎯',
        texto: `${producto.nombre} esta a ${euros(barato.precio, barato.moneda)} en ` +
               `${barato.tienda}: ha llegado a tu precio.`,
      });
    }

    const vigilada = deHoy.find((p) => p.tienda === TIENDA_VIGILADA && p.bajada);
    if (vigilada && vigilada.bajada.desde > vigilada.precio) {
      avisos.push({
        clase: 'bajada',
        icono: '⬇',
        texto: `${producto.nombre} ha bajado en ${TIENDA_VIGILADA} a ` +
               `${euros(vigilada.precio, vigilada.moneda)}, desde ` +
               `${euros(vigilada.bajada.desde, vigilada.moneda)}.`,
      });
    }
  }

  return avisos;
}

function pintarAvisos(datos) {
  const caja = document.getElementById('avisos');
  if (!caja) return;

  const avisos = avisosDeOfertas(datos);
  if (!avisos.length) return;   // vacio se queda sin ocupar sitio

  caja.innerHTML = avisos.map((aviso) => `
    <a class="aviso-precio ${aviso.clase}" href="ofertas.html">
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
      <span class="aviso-icono" aria-hidden="true">⚠</span>
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


async function cargarPortada() {
  const entradas = document.querySelectorAll('.entrada[data-json]');

  await Promise.all(Array.from(entradas, async (entrada) => {
    let datos;
    try {
      const resp = await fetch(entrada.dataset.json + '?v=' + Date.now());
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      datos = await resp.json();
    } catch (e) {
      return;  // la entrada se queda con lo que trae escrito
    }

    const esOfertas = entrada.dataset.tipo === 'ofertas';
    if (esOfertas) pintarAvisos(datos);

    const resumen = esOfertas ? deOfertas(datos) : deNoticias(datos);

    const titulo = entrada.querySelector('.entrada-titulo');
    if (titulo) titulo.textContent = resumen.titulo;

    const desde = entrada.querySelector('.entrada-cuando');
    if (desde) desde.textContent = resumen.cuando;

    entrada.classList.toggle('vacia', !resumen.hayAlgo);

    const marca = entrada.querySelector('.nuevo');
    if (marca && resumen.hayAlgo && datos.actualizado !== visto(entrada.dataset.id)) {
      marca.hidden = false;
    }
  }));
}

cargarPortada().then(pintarVigilancia);
