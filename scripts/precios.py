#!/usr/bin/env python3
"""Precios de la seccion de Ofertas.

Consulta las fichas de scripts/productos.json y escribe data/ofertas.json. Aqui
no hay nada que decidir: el precio se lee del bloque Product que las tiendas
incrustan en su HTML para Google, no del criterio de nadie. Por eso este paso
lo hace un script entero y la rutina solo lo lanza.

    python3 scripts/precios.py consultar
    python3 scripts/precios.py probar <url> [--navegador]

Biblioteca estandar, salvo las tiendas marcadas con "navegador": true en
productos.json, que necesitan Playwright. Comparte utilidades con noticias.py.
"""

import argparse
import json
import re
import sys
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from noticias import (AGENTE, ESPANA, FORMATO_FECHA, FORMATO_FECHA_HORA,
                      escribir_json, leer_json)

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = Path(__file__).resolve().parent / "productos.json"
SALIDA = RAIZ / "data" / "ofertas.json"

# Estados de un precio, tal como los pinta la web:
#   ok    -> consultado ahora mismo
#   viejo -> la consulta fallo y se conserva el de la ejecucion anterior
#   nuevo -> producto recien anadido que todavia no se ha podido consultar
OK, VIEJO, NUEVO = "ok", "viejo", "nuevo"

# Tiendas que solo responden desde una conexion domestica (MediaMarkt da 403 a
# cualquier servidor). No se consultan desde el workflow: se dejan en la web
# con su enlace y su ultimo precio conocido, fechado. Asi el usuario puede
# mirar el precio el mismo, en vez de perder la tienda de vista.
ENLACE = "enlace"

# Reintentos de descarga ante un corte de red, y espera (en segundos) antes de
# cada uno. La espera crece con el intento para no insistir sobre una tienda
# que este teniendo un mal momento.
INTENTOS = 3
ESPERA_REINTENTO = 3

# Un navegador normal y corriente. Sin esto Playwright se presenta como
# "HeadlessChrome" y las tiendas que filtran robots lo cazan igual.
AGENTE_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36")

# Tope (segundos) que se le da a una ficha para montar su bloque de producto.
# No es una espera fija: se sondea y se sale en cuanto aparece, asi que las
# tiendas rapidas no lo pagan y solo las lentas gastan el margen entero.
#
# Medido el 12-08-2026 en las cuatro tiendas con navegador: cuando la carga va
# bien, el bloque ya esta al primer segundo. Lo que agotaba el margen no eran
# fichas lentas sino paginas que nunca iban a traerlo, asi que un tope generoso
# solo servia para tardar mas en darse por vencido.
ESPERA_RENDER_MAX = 12

# Segundos minimos entre dos peticiones a la misma tienda. Xtralife empezo a
# fallar cuando el catalogo crecio: devolvia la ficha sin su bloque de producto
# aunque el bloque existiera, y solo ella, unas 3 de cada 8 veces. Pedirle tres
# fichas casi seguidas no es pasar por una visita normal, que es justo lo que
# hace que todo esto funcione. Con la cadencia diaria, estos segundos no
# cuestan nada.
PAUSA_MISMA_TIENDA = 4

# Una pagina de error del servidor, que llega con el estado 200 de la peticion
# original porque la tienda navega a ella despues. Reconocerla por el titulo
# evita quedarse los 30 segundos del sondeo esperando un bloque de producto en
# una pagina que solo dice "502 Bad Gateway".
ERROR_DE_SERVIDOR = re.compile(
    r"<title>[^<]*(50[0234]|bad gateway|service unavailable|gateway time)",
    re.I)

# IVA general espanol. Hace falta porque hay tiendas que publican el precio sin
# el, y ese numero no es el que paga nadie.
IVA = 1.21

# Red de seguridad contra un precio bien formado pero absurdo, como la cuota de
# 2,07 EUR que Orange declara donde deberia ir el precio. Un precio por debajo
# de esta parte de la mediana del dia no se publica.
#
# 0.25 esta elegido para no tocar una rebaja de verdad: un juego al 25% de lo
# que piden las demas tiendas el mismo dia no es una oferta, es otra cosa. La
# cuota de Orange era el 4%, asi que cae con muchisimo margen.
FACTOR_SOSPECHA = 0.25

# Con uno o dos precios no hay mediana que valga: el sospechoso podria ser
# justo el que marca la referencia. Se prefiere no juzgar a juzgar mal.
MINIMO_PARA_JUZGAR = 3


class Navegador:
    """Chromium de verdad, para las tiendas que dan 403 a un script pelado.

    Probado el 10-08-2026 desde el runner: MediaMarkt y PcComponentes devuelven
    403 a urllib y precio a esto, en la misma IP y con segundos de diferencia.
    O sea que lo que filtran no es la direccion, es parecer un script. Por eso
    el navegador va por tienda y no para todas: GAME responde a urllib en
    milisegundos y arrancarle un Chromium seria pagar 20 segundos por nada.

    Se abre uno solo por ejecucion y se reaprovecha para todas las fichas:
    arrancarlo es lo caro, cada pagina despues sale casi gratis.
    """

    def __init__(self):
        self._playwright = None
        self._navegador = None
        # Cuando se pidio la ultima ficha a cada tienda, para no encadenarlas.
        self._ultima_visita = {}

    def _arrancar(self):
        if self._navegador:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "falta Playwright, que necesitan las tiendas marcadas con "
                "\"navegador\": true en productos.json. Instalalo con: "
                "pip install playwright && playwright install chromium"
            )
        self._playwright = sync_playwright().start()
        self._navegador = self._playwright.chromium.launch()

    def _esperar_turno(self, url):
        """Deja pasar un rato entre dos fichas de la misma tienda."""
        dominio = url.split("/")[2] if "//" in url else url
        pendiente = (self._ultima_visita.get(dominio, 0)
                     + PAUSA_MISMA_TIENDA - time.monotonic())
        if pendiente > 0:
            time.sleep(pendiente)
        return dominio

    def html(self, url):
        """HTML de una ficha ya renderizada, reintentando los 403 pasajeros."""
        self._arrancar()
        dominio = self._esperar_turno(url)
        for intento in range(INTENTOS):
            contexto = self._navegador.new_context(
                # Con el User-Agent por defecto pone "HeadlessChrome" y volvemos
                # a estar donde estabamos: anunciandonos como un robot.
                user_agent=AGENTE_NAVEGADOR,
                locale="es-ES",
                viewport={"width": 1366, "height": 768},
            )
            try:
                pagina = contexto.new_page()
                respuesta = pagina.goto(url, wait_until="domcontentloaded",
                                        timeout=45000)
                estado = respuesta.status if respuesta else 0
                if estado >= 400:
                    # Aqui si se reintenta un 403, al reves que en urllib: el de
                    # PcComponentes resulto ser intermitente (403 en una pasada
                    # y precio en la siguiente, 15 minutos despues).
                    raise RuntimeError(f"HTTP {estado}")
                # Se espera al bloque de producto en si, no un rato fijo ni a
                # que la red se calme. Con una espera de 4 segundos Xtralife
                # fallaba a veces con "no trae ningun bloque de producto", que
                # es lo que se ve cuando el JavaScript aun no ha montado la
                # ficha; y esperar por si acaso penaliza a las que ya estaban
                # listas. Sondeando se sale en cuanto aparece.
                #
                # Sirve para las dos formas de publicarlo, la etiqueta ld+json
                # de GAME y el estado interno de MediaMarkt, porque pregunta
                # por el dato y no por un elemento concreto del DOM.
                limite = time.monotonic() + ESPERA_RENDER_MAX
                while True:
                    try:
                        html = pagina.content()
                    except Exception:
                        # "the page is navigating and changing the content":
                        # se ha pedido el HTML justo mientras la ficha navegaba.
                        # No es un fallo de la tienda, es haber preguntado en
                        # mal momento, asi que se vuelve a mirar luego. Paso en
                        # el runner con Xtralife y nunca en local: depende de lo
                        # que tarde la red.
                        html = ""
                    if html and objetos_producto(html):
                        return html
                    if html and ERROR_DE_SERVIDOR.search(html):
                        # La tienda se ha caido para esta peticion. Esperar mas
                        # no la levanta, asi que se corta ya y se reintenta tras
                        # la pausa, que es lo unico que puede ayudar.
                        raise RuntimeError(
                            "la tienda ha devuelto una pagina de error de "
                            "servidor (5xx), no la ficha")
                    if time.monotonic() >= limite:
                        break
                    pagina.wait_for_timeout(500)
                # Puede que la ficha no publique bloque nunca, o que hoy vaya
                # lenta. Se reintenta por lo segundo; si es lo primero, el
                # ultimo intento acaba fallando igual.
                raise RuntimeError("la pagina no trae ningun bloque de "
                                   "producto")
            except Exception:
                if intento == INTENTOS - 1:
                    raise
                time.sleep(ESPERA_REINTENTO * (intento + 1))
            finally:
                # Cuenta desde que se suelta la ficha, no desde que se pidio:
                # lo que se quiere espaciar son las visitas, y una pagina lenta
                # ya ha ocupado a la tienda todo ese rato.
                self._ultima_visita[dominio] = time.monotonic()
                contexto.close()

    def cerrar(self):
        if self._navegador:
            self._navegador.close()
        if self._playwright:
            self._playwright.stop()


def descargar(peticion):
    """Bytes de una ficha, reintentando los cortes de red pasajeros.

    Un timeout suelto no significa que la tienda bloquee: la misma URL que
    fallo aqui responde al segundo intento. Y como casi todo el catalogo son
    tiendas de solo enlace, un unico timeout puede dejar la ejecucion con cero
    precios, que es justo el caso en el que el workflow falla a proposito.

    Solo se reintentan los fallos de red. Un 403 es una respuesta, no un corte:
    repetirlo tres veces alarga la ejecucion para llegar al mismo sitio.
    """
    for intento in range(INTENTOS):
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                return respuesta.read(), respuesta.headers.get_content_charset()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if intento == INTENTOS - 1:
                raise
            time.sleep(ESPERA_REINTENTO * (intento + 1))


def traer(url):
    """HTML de una ficha, decodificado con la codificacion que diga la tienda."""
    peticion = urllib.request.Request(url, headers={
        "User-Agent": AGENTE,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es-ES,es;q=0.9",
    })
    crudo, declarada = descargar(peticion)
    codificaciones = [declarada, "utf-8", "cp1252"]
    for codificacion in codificaciones:
        if not codificacion:
            continue
        try:
            return crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return crudo.decode("utf-8", "replace")


def aplanar(datos):
    """Un JSON-LD puede ser un objeto, una lista o traer un @graph dentro."""
    if isinstance(datos, list):
        for elemento in datos:
            yield from aplanar(elemento)
    elif isinstance(datos, dict):
        yield datos
        for elemento in datos.get("@graph", []) or []:
            yield from aplanar(elemento)


def es_producto(objeto):
    """Si el @type de un objeto JSON-LD dice que es un producto.

    Sin mirar mayusculas y aceptando lista: el estandar dice "Product", pero
    PcComponentes lo escribe en minuscula y otras tiendas ponen varios tipos a
    la vez. Exigir la forma exacta descarta fichas que traen el precio bien.
    """
    tipo = objeto.get("@type")
    tipos = tipo if isinstance(tipo, list) else [tipo]
    return any(isinstance(t, str) and t.lower() == "product" for t in tipos)


def objetos_producto(html):
    """Objetos JSON de tipo Product que haya en la pagina.

    Las dos tiendas lo publican de forma distinta y hay que cubrir las dos:
    GAME usa una etiqueta <script type="application/ld+json"> con el JSON
    indentado, y MediaMarkt lo mete comprimido dentro del estado interno de la
    pagina, sin etiqueta propia. Para eso segundo se busca la marca en todo el
    HTML y se recorta el objeto contando llaves, saltandose las que van dentro
    de una cadena de texto.
    """
    encontrados = []

    for bloque in re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.S | re.I):
        try:
            datos = json.loads(bloque)
        except json.JSONDecodeError:
            continue
        encontrados.extend(d for d in aplanar(datos) if es_producto(d))

    for marca in re.finditer(r'\{\s*"@type"\s*:\s*"[Pp]roduct"', html):
        inicio = marca.start()
        nivel, i, en_cadena, escapado = 0, inicio, False, False
        while i < len(html):
            caracter = html[i]
            if escapado:
                escapado = False
            elif caracter == "\\":
                escapado = True
            elif caracter == '"':
                en_cadena = not en_cadena
            elif not en_cadena:
                if caracter == "{":
                    nivel += 1
                elif caracter == "}":
                    nivel -= 1
                    if nivel == 0:
                        break
            i += 1
        try:
            encontrados.append(json.loads(html[inicio:i + 1]))
        except json.JSONDecodeError:
            continue
    return encontrados


def referencia_de(url):
    """El numero largo de la URL, que es como la tienda identifica la ficha."""
    numeros = re.findall(r"\d{5,}", url)
    return numeros[-1] if numeros else ""


def oferta_de(producto, url=""):
    """La oferta de la que sacar el precio, que no siempre es la primera.

    Una ficha puede traer un AggregateOffer, que no es una oferta sino el
    resumen de varias: `lowPrice` es la mas barata de todas, y esa puede ser de
    otro vendedor. Paso con The Adventures of Elliot en PcComponentes, que
    resume dos ofertas con `lowPrice: 49` y `highPrice: 61.99` cuando el precio
    de la tienda son los 61,99. Con Star Fox no se noto porque solo habia una
    oferta y los dos valores coincidian.

    Asi que ante un agregado se busca la oferta concreta de la ficha pedida,
    comparando su URL. Si no se puede identificar, se prefiere `highPrice` a
    `lowPrice`: publicar de mas es un error visible que se corrige mirando la
    tienda, y publicar de menos es un reclamo falso que nadie comprueba.
    """
    oferta = producto.get("offers") or {}
    if isinstance(oferta, list):
        oferta = oferta[0] if oferta else {}
    if not isinstance(oferta, dict):
        return {}

    tipo = str(oferta.get("@type", "")).lower()
    if tipo != "aggregateoffer":
        return oferta

    dentro = oferta.get("offers") or []
    if isinstance(dentro, dict):
        dentro = [dentro]
    dentro = [o for o in dentro if isinstance(o, dict) and o.get("price") is not None]

    pedida = url.split("?")[0].rstrip("/").lower()
    for o in dentro:
        suya = str(o.get("url", "")).split("?")[0].rstrip("/").lower()
        if suya and pedida and suya.endswith(pedida.split("//")[-1]):
            return o
    if len(dentro) == 1:
        return dentro[0]
    # Sin forma de identificar cual es la de la tienda: el resumen, pero sin
    # su lowPrice, que es de quien sea.
    resumen = dict(oferta)
    resumen.pop("lowPrice", None)
    return resumen


def leer_precio(html, url):
    """(precio, datos) del producto de esta URL, o (None, motivo del fallo).

    Una ficha trae ademas productos relacionados y variantes, cada uno con su
    precio. Por eso se elige el objeto que lleva dentro la referencia de la URL
    pedida, y solo si no aparece ninguno se cae al primero que tenga precio.
    """
    productos = objetos_producto(html)
    if not productos:
        return None, "la pagina no trae ningun bloque de producto"

    referencia = referencia_de(url)
    candidatos = [p for p in productos
                  if referencia and referencia in json.dumps(p, ensure_ascii=False)]
    for producto in candidatos or productos:
        oferta = oferta_de(producto, url)
        bruto = (oferta.get("price") or oferta.get("highPrice")
                 or oferta.get("lowPrice"))
        if bruto is None:
            continue
        try:
            precio = round(float(str(bruto).replace(",", ".")), 2)
        except ValueError:
            continue
        vendedor = oferta.get("seller")
        if isinstance(vendedor, dict):
            vendedor = vendedor.get("name")
        # None = la ficha no dice nada del stock, que no es lo mismo que decir
        # que no hay. GAME, por ejemplo, no lo declara: marcarlo como agotado
        # seria publicar algo falso.
        existencias = oferta.get("availability")
        return precio, {
            "nombre_ficha": str(producto.get("name", ""))[:120],
            "moneda": oferta.get("priceCurrency") or "EUR",
            "disponible": str(existencias).endswith("InStock") if existencias else None,
            "vendedor": vendedor if isinstance(vendedor, str) else None,
            "elegido_por_referencia": bool(candidatos),
        }
    return None, "hay bloques de producto pero ninguno trae precio"


def de_cuota_a_contado(cuota, meses):
    """Precio de contado a partir de una cuota mensual publicada sin IVA.

    Orange no publica el precio del producto: su bloque Product trae la cuota
    de una financiacion, y ademas sin IVA. Con la ficha de Star Fox se vio la
    cadena entera: 59,99 / 1,21 / 24 = 2,07, que es exactamente lo que declara,
    y 2,07 x 1,21 = 2,50, que es lo que pinta en pantalla.

    Ojo con lo que sale de aqui: 2,07 x 1,21 x 24 da 60,11 y el PVP es 59,99.
    Los 12 centimos son el redondeo de la cuota, que viene con dos decimales.
    O sea que esto es una reconstruccion con un error de unos centimos, no un
    precio leido, y por eso el registro se marca con "estimado": true y la web
    lo avisa. El plazo tampoco esta en la ficha: lo pone el catalogo.
    """
    return round(cuota * IVA * meses, 2)


def descartar_absurdos(precios, anteriores, id_producto):
    """Quita los precios que no pueden ser de este producto.

    Un precio puede estar perfectamente formado y aun asi no ser un precio: la
    cuota de Orange lo demuestra. Como se detecto leyendo una ficha a mano, y a
    mano no se van a leer todos los dias, aqui se automatiza el olfato: se
    compara cada precio con la mediana de los del mismo dia, que es la mejor
    referencia disponible de lo que vale el producto.

    Se usa la mediana y no la media justo porque el valor sospechoso arrastraria
    la media hacia abajo y podria acabar tapandose a si mismo.

    Devuelve la lista de avisos; los precios se degradan en el sitio.
    """
    frescos = [p for p in precios
               if p.get("estado") == OK and p.get("precio") is not None]
    if len(frescos) < MINIMO_PARA_JUZGAR:
        return []

    umbral = statistics.median(p["precio"] for p in frescos) * FACTOR_SOSPECHA
    avisos = []
    for p in frescos:
        if p["precio"] >= umbral:
            continue
        avisos.append(
            f"{p['tienda']}: {p['precio']:.2f} EUR es menos del "
            f"{FACTOR_SOSPECHA:.0%} de lo que piden las demas hoy (umbral "
            f"{umbral:.2f}). No se publica: casi seguro que la ficha no da el "
            f"precio del producto, sino una cuota, un accesorio o una variante. "
            f"Si el precio es real, mirar la ficha y anadir 'cuota' o corregir "
            f"la URL en productos.json."
        )
        # Se degrada como cualquier otro fallo: con el ultimo precio bueno si
        # lo hay. Publicar el absurdo seria peor que no publicar nada.
        anterior = anteriores.get((id_producto, p["tienda"]), {})
        conservado = dict(anterior) if anterior else {}
        conservado.update({
            "tienda": p["tienda"],
            "enlace": p["enlace"],
            "estado": VIEJO if anterior else NUEVO,
        })
        conservado.setdefault("precio", None)
        precios[precios.index(p)] = conservado
    return avisos


def previos():
    """Lo publicado en la ejecucion anterior, indexado por producto y tienda."""
    if not SALIDA.exists():
        return {}
    guardado = {}
    for producto in leer_json(SALIDA).get("productos", []):
        for precio in producto.get("precios", []):
            guardado[(producto.get("id"), precio.get("tienda"))] = precio
    return guardado


def cmd_consultar(args):
    catalogo = leer_json(CATALOGO).get("productos", [])
    if not catalogo:
        print("ERROR: scripts/productos.json no tiene ningun producto.")
        return 1

    ahora = datetime.now(ESPANA)
    anteriores = previos()
    salida, fallos, consultados = [], [], 0
    # Se crea siempre pero no arranca nada hasta la primera ficha que lo pida:
    # si el catalogo no tiene ninguna tienda con navegador, no se paga.
    navegador = Navegador()

    for producto in catalogo:
        precios = []
        for tienda in producto.get("tiendas", []):
            clave = (producto["id"], tienda["tienda"])
            anterior = anteriores.get(clave, {})
            etiqueta = f"{producto['nombre']} en {tienda['tienda']}"

            if tienda.get("solo_enlace"):
                # Ni se intenta: se sabe que va a fallar y un fallo esperado
                # ensucia el parte y hace dudar de los que si importan.
                conservado = dict(anterior)
                conservado.update({
                    "tienda": tienda["tienda"],
                    "enlace": tienda["url"],
                    "estado": ENLACE,
                })
                conservado.setdefault("precio", None)
                precios.append(conservado)
                visto = anterior.get("consultado", "nunca")
                print(f"{etiqueta}: solo enlace (ultimo precio visto: {visto})")
                continue

            try:
                if tienda.get("navegador"):
                    html = navegador.html(tienda["url"])
                else:
                    html = traer(tienda["url"])
                precio, extra = leer_precio(html, tienda["url"])
            except Exception as e:  # red, timeout, 403, 404...
                precio, extra = None, str(e)

            if precio is None:
                fallos.append(f"{etiqueta}: {extra}")
                if anterior:
                    # Se conserva el ultimo precio conocido marcado como viejo:
                    # borrarlo dejaria la web con un hueco, e inventarlo seria
                    # peor todavia.
                    conservado = dict(anterior)
                    conservado["estado"] = VIEJO
                    precios.append(conservado)
                else:
                    precios.append({
                        "tienda": tienda["tienda"],
                        "enlace": tienda["url"],
                        "estado": NUEVO,
                        "precio": None,
                    })
                continue

            # Tiendas que publican una cuota en vez del precio: se reconstruye
            # el contado antes de comparar nada, porque una cuota compitiendo
            # con precios enteros ganaria siempre "Mas barato".
            cuota = tienda.get("cuota")
            estimado = None
            if cuota:
                mensual = precio
                precio = de_cuota_a_contado(mensual, cuota["meses"])
                estimado = {
                    "cuota": mensual,
                    "meses": cuota["meses"],
                    "iva": round((IVA - 1) * 100),
                }

            consultados += 1
            minimo = anterior.get("minimo")
            minimo_fecha = anterior.get("minimo_fecha")
            if minimo is None or precio < minimo:
                minimo, minimo_fecha = precio, ahora.strftime(FORMATO_FECHA)

            registro = {
                "tienda": tienda["tienda"],
                "precio": precio,
                "moneda": extra["moneda"],
                "disponible": extra["disponible"],
                "vendedor": extra["vendedor"],
                "enlace": tienda["url"],
                "consultado": ahora.strftime(FORMATO_FECHA_HORA),
                "minimo": minimo,
                "minimo_fecha": minimo_fecha,
                "estado": OK,
            }
            if estimado:
                registro["estimado"] = estimado
            precios.append(registro)

            aviso = "" if extra["elegido_por_referencia"] else "  (ojo: ficha elegida por descarte)"
            stock = " [sin stock]" if extra["disponible"] is False else ""
            calculo = (f"  (calculado: {estimado['cuota']:.2f} x {estimado['meses']} "
                       f"cuotas + IVA)") if estimado else ""
            print(f"{etiqueta}: {precio:.2f} {extra['moneda']}{stock}{calculo}{aviso}")

        # Ya con todos los precios del producto delante, que es cuando se puede
        # saber si alguno se sale de lo que piden los demas.
        for aviso in descartar_absurdos(precios, anteriores, producto["id"]):
            fallos.append(f"{producto['nombre']} en {aviso}")
            consultados -= 1

        salida.append({
            "id": producto["id"],
            "nombre": producto["nombre"],
            "plataforma": producto.get("plataforma", ""),
            "precios": precios,
        })

    navegador.cerrar()

    escribir_json(SALIDA, {
        "seccion": "ofertas",
        "actualizado": ahora.strftime(FORMATO_FECHA_HORA),
        "productos": salida,
    })

    for fallo in fallos:
        print(f"FALLO {fallo}")
    print(f"\nEscrito data/ofertas.json: {len(salida)} productos, "
          f"{consultados} precios consultados, {len(fallos)} fallos.")
    # Los fallos no tumban la ejecucion: la web se queda con el precio anterior
    # marcado como viejo, que es mejor que no publicar nada.
    return 0


def cmd_probar(args):
    """Para comprobar una ficha antes de meterla en el catalogo."""
    navegador = Navegador() if args.navegador else None
    try:
        html = navegador.html(args.url) if navegador else traer(args.url)
        precio, extra = leer_precio(html, args.url)
    except Exception as e:
        print(f"ERROR: no se ha podido abrir la ficha: {e}")
        if not args.navegador:
            # El 403 de un script no significa que la tienda este cerrada:
            # MediaMarkt, PcComponentes y Xtralife lo dan aqui y sueltan el
            # precio con --navegador.
            print("Prueba otra vez con --navegador antes de descartarla.")
        return 1
    finally:
        if navegador:
            navegador.cerrar()
    if precio is None:
        print(f"ERROR: {extra}. Esta tienda no sirve para el catalogo.")
        if not args.navegador:
            print("Prueba otra vez con --navegador: puede que la ficha monte "
                  "el precio con JavaScript, como hace Xtralife.")
        return 1
    print(f"Ficha    : {extra['nombre_ficha']}")
    if args.cuotas:
        contado = de_cuota_a_contado(precio, args.cuotas)
        print(f"Cuota    : {precio:.2f} {extra['moneda']}/mes sin IVA")
        print(f"Contado  : {contado:.2f} {extra['moneda']}  (calculado: "
              f"cuota x {args.cuotas} x IVA, con unos centimos de error)")
        precio = contado
    else:
        print(f"Precio   : {precio:.2f} {extra['moneda']}")
    print(f"Stock    : {'si' if extra['disponible'] else 'no'}")
    if extra["vendedor"]:
        print(f"Vendedor : {extra['vendedor']}")
    if not extra["elegido_por_referencia"]:
        print("AVISO: la URL no lleva referencia reconocible y se ha cogido el "
              "primer producto con precio de la pagina. Comprueba que el nombre "
              "de arriba es el juego que quieres.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    ordenes = parser.add_subparsers(dest="orden", required=True)

    p = ordenes.add_parser("consultar", help="escribe data/ofertas.json")
    p.set_defaults(func=cmd_consultar)

    p = ordenes.add_parser("probar", help="comprueba una ficha suelta")
    p.add_argument("url")
    p.add_argument("--navegador", action="store_true",
                   help="abrir la ficha con Chromium, como las tiendas que "
                        "dan 403 a un script o montan el precio con JavaScript")
    p.add_argument("--cuotas", type=int, metavar="MESES",
                   help="la ficha publica una cuota mensual sin IVA en vez del "
                        "precio (Orange): reconstruir el contado con este plazo")
    p.set_defaults(func=cmd_probar)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
