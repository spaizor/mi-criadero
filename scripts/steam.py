#!/usr/bin/env python3
"""Actualiza data/steam.json con el precio de hoy de los juegos de Steam.

La seccion de Steam es hermana de la de Ofertas y nace de la misma idea: no
busca rebajas, sigue una lista cerrada que vive en scripts/juegos-steam.json.
Lo que cambia es de donde sale el precio, y ese cambio lo simplifica todo.

Ofertas abre la ficha de cada tienda y le saca el precio del bloque
schema.org, con Chromium para las cuatro tiendas que rechazan a los scripts.
Aqui no hace falta nada de eso: Steam publica una API que devuelve el precio
ya estructurado. Medido el 18-09-2026 contra este mismo catalogo:

    50 juegos     ->  2 peticiones, 0,35 s cada una, unos 4 KB
    17 ediciones  ->  1 peticion cada una (packagedetails no admite lote)

O sea que la pasada entera son segundos y solo biblioteca estandar, como
noticias.py y al reves que precios.py, que necesita Playwright.

    python3 scripts/steam.py consultar          escribe data/steam.json
    python3 scripts/steam.py probar <appid>     una ficha suelta, sin publicar
    python3 scripts/steam.py descubrir          rellena el catalogo
    python3 scripts/steam.py frescura           la pasada de hoy, ha salido?

Lo que NO hace, y no es un descuido:

  - No lee la lista de deseados en cada pasada. Podria (el endpoint es publico
    y no pide clave), pero eso obligaria a escribir el SteamID del usuario en
    un repositorio publico. El catalogo se copio una vez y se congelo;
    refrescarlo se hace a mano.
  - No hay precio objetivo todavia. Se anadira cuando el usuario pase su
    lista, y entonces sale casi gratis: la web ya sabe pintarlo en Ofertas.
  - No consulta otras tiendas. Eso sera ITAD, mas adelante.
"""

import argparse
import gzip
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, time as hora_del_dia, timedelta, timezone
from pathlib import Path

from noticias import (AGENTE, ESPANA, FORMATO_FECHA, FORMATO_FECHA_HORA,
                      escribir_json, leer_json)

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = Path(__file__).resolve().parent / "juegos-steam.json"
SALIDA = RAIZ / "data" / "steam.json"

# La evolucion de cada precio, un fichero por mes. Por los mismos motivos que
# en precios.py: asi un mes cerrado no se vuelve a tocar y el repositorio no
# engorda reescribiendo los mismos numeros en cada pasada.
SERIES = RAIZ / "data" / "steam-precios"

# Estados de un precio, tal como los pinta la web:
#   ok           -> consultado en esta pasada
#   viejo        -> la consulta fallo y se conserva el de la pasada anterior
#   nuevo        -> juego recien anadido, todavia sin consultar
#   proximamente -> anunciado, pero sin fecha ni precio
#   retirado     -> ya salio, pero Steam ya no lo vende
#
# Los dos ultimos no son fallos y por eso tienen nombre propio: la ficha los
# distingue sola con release_date.coming_soon, y publicarlos como un "sin
# precio" comun perderia la diferencia. Es la misma idea que el
# 'disponible: null' de Ofertas: no declarar el stock no es estar agotado.
OK, VIEJO, NUEVO, PROXIMAMENTE, RETIRADO = (
    "ok", "viejo", "nuevo", "proximamente", "retirado")

API = "https://store.steampowered.com/api"
FICHA = "https://store.steampowered.com/app/{}/"
FICHA_PACK = "https://store.steampowered.com/sub/{}/"

# El pais fija la moneda, y esto NO es cosmetico. Sin 'cc', Steam responde en
# la moneda de la IP que pregunta, y el runner de GitHub puede estar en
# cualquier region: un dolar publicado como euro no rompe nada visible, que es
# justo el tipo de fallo que este proyecto persigue. Por eso ademas se
# comprueba al leer que lo que vuelve viene en EUR.
PAIS = "es"
IDIOMA = "spanish"
MONEDA = "EUR"

# Medido: con filters=price_overview la API acepta varios appids en una sola
# peticion y con 30 responde en 0,35 s. Con otros filtros (basic) admite uno
# solo y devuelve null, asi que este numero va atado a ESE filtro.
POR_LOTE = 30

INTENTOS = 3
ESPERA_REINTENTO = 3

# Entre peticiones sueltas. La API aguanta de sobra (diez seguidas sin un solo
# estrangulamiento al medirla), pero ir espaciado no cuesta nada y su limite
# conocido es por IP: el runner comparte la suya con mucha gente.
PAUSA = 0.4

# Cuantos juegos pueden quedarse sin precio antes de dar la pasada por mala.
# No se exige que entren todos porque algunos no tienen precio POR DISENO
# (proximamente, retirado) y eso no es un fallo; lo que no puede pasar es que
# no entre ninguno, que es el sintoma de que la API ha dejado de responder.
MINIMO_PARA_PUBLICAR = 1


# --------------------------------------------------------------------------
# Descarga
# --------------------------------------------------------------------------

def descargar(url):
    """Bytes de una respuesta de la API, reintentando los cortes de red.

    Solo se reintentan los fallos de red. Un codigo HTTP es una respuesta, no
    un corte: repetirlo tres veces alarga la pasada para llegar al mismo sitio.
    """
    peticion = urllib.request.Request(url, headers={
        "User-Agent": AGENTE,
        "Accept": "application/json",
        "Accept-Language": "es-ES,es;q=0.9",
    })
    for intento in range(INTENTOS):
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                return respuesta.read()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if intento == INTENTOS - 1:
                raise
            time.sleep(ESPERA_REINTENTO * (intento + 1))


def pedir(url):
    """El JSON de una llamada a la API.

    Steam comprime aunque no se le pida, e ignora un 'Accept-Encoding:
    identity': su respuesta a filters=basic con varios appids llega en gzip sin
    anunciarlo en ninguna cabecera. Es el mismo caso que Vandal, que estuvo
    meses dado por bloqueado cuando lo unico que pasaba es que no se
    descomprimia, asi que aqui se mira el numero magico 1f 8b igual que en
    noticias.py y no la cabecera, que no todos la mandan bien.
    """
    crudo = descargar(url)
    if crudo[:2] == b"\x1f\x8b":
        crudo = gzip.decompress(crudo)
    return json.loads(crudo.decode("utf-8"))


def euros(centimos):
    """La API da los precios en centimos enteros, que es lo comodo para ella."""
    return None if centimos is None else round(centimos / 100, 2)


# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------

def plano(texto):
    """Minusculas y sin tildes SIN cambiar la longitud del texto.

    Lo de la longitud importa porque con esto se corta por indice, y la
    normalizacion de compatibilidad descompone el simbolo de marca registrada
    en dos letras: 'Edicion Completa de Stellar Blade(tm)' salia recortada como
    'Edicion Complet'. Para comparar valdria cualquier version; para cortar, no.
    """
    fuera = []
    for letra in texto:
        suelta = "".join(c for c in unicodedata.normalize("NFD", letra)
                         if not unicodedata.combining(c))
        fuera.append(suelta if len(suelta) == 1 else letra)
    return "".join(fuera).lower()


def clave(texto):
    """Para comparar dos nombres ignorando puntuacion, tildes y mayusculas."""
    return re.sub(r"[^a-z0-9]+", "", plano(texto))


def identificador(nombre):
    """El 'id' de un juego, que es lo que conserva su minimo historico."""
    limpio = plano(nombre).replace("&", " y ")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", limpio)).strip("-")[:48]


# --------------------------------------------------------------------------
# El catalogo
# --------------------------------------------------------------------------

def leer_catalogo():
    datos = leer_json(CATALOGO)
    juegos = datos.get("juegos", [])
    if not juegos:
        raise SystemExit(
            f"ERROR: {CATALOGO.name} no tiene ningun juego. Sin catalogo no hay "
            "nada que consultar: anade al menos un bloque con su 'appid'.")
    sin_appid = [j.get("nombre", "?") for j in juegos if not j.get("appid")]
    if sin_appid:
        raise SystemExit(
            f"ERROR: estos juegos de {CATALOGO.name} no tienen 'appid': "
            f"{', '.join(sin_appid)}. El appid es el numero de la URL de la "
            "ficha, y sin el no se puede preguntar nada.")
    return datos, juegos


# --------------------------------------------------------------------------
# Precios
# --------------------------------------------------------------------------

def de_precio(bloque):
    """Normaliza un precio de la API, venga de un juego o de un pack.

    Se comprueba la moneda porque es la unica forma de cazar que una pasada ha
    salido con el pais equivocado: los numeros serian perfectamente validos y
    perfectamente falsos.
    """
    if not bloque:
        return None
    moneda = bloque.get("currency")
    if moneda != MONEDA:
        raise ValueError(
            f"la API ha respondido en {moneda!r} y no en {MONEDA}. Steam usa la "
            "moneda de la IP que pregunta cuando no se le fija el pais, asi que "
            f"revisa que las llamadas lleven cc={PAIS}.")
    return {
        "precio": euros(bloque.get("final")),
        "base": euros(bloque.get("initial")),
        "descuento": bloque.get("discount_percent") or 0,
        "moneda": moneda,
    }


def precios_de_juegos(appids):
    """El precio de cada juego, en lotes.

    Devuelve {appid: precio}, donde precio puede ser None (el juego existe pero
    no esta a la venta). Los appids que no aparezcan son fichas que la API no
    reconoce, y esos los trata 'consultar' conservando lo anterior.
    """
    fuera = {}
    for desde in range(0, len(appids), POR_LOTE):
        lote = appids[desde:desde + POR_LOTE]
        respuesta = pedir(
            f"{API}/appdetails?appids={','.join(str(a) for a in lote)}"
            f"&cc={PAIS}&l={IDIOMA}&filters=price_overview")
        for appid in lote:
            entrada = (respuesta or {}).get(str(appid)) or {}
            if not entrada.get("success"):
                continue
            fuera[appid] = de_precio(
                (entrada.get("data") or {}).get("price_overview"))
        if desde + POR_LOTE < len(appids):
            time.sleep(PAUSA)
    return fuera


def precio_de_edicion(packageid):
    """El precio de un pack. packagedetails no admite lote: con varios da 400."""
    entrada = (pedir(f"{API}/packagedetails?packageids={packageid}"
                     f"&cc={PAIS}&l={IDIOMA}") or {}).get(str(packageid)) or {}
    if not entrada.get("success"):
        return None
    precio = (entrada.get("data") or {}).get("price") or {}
    if not precio:
        return None
    return de_precio({
        "currency": precio.get("currency"),
        "final": precio.get("final"),
        "initial": precio.get("initial"),
        "discount_percent": precio.get("discount_percent"),
    })


def ficha_completa(appid):
    """La ficha entera, que es la unica que trae package_groups."""
    entrada = (pedir(f"{API}/appdetails?appids={appid}&cc={PAIS}&l={IDIOMA}")
               or {}).get(str(appid)) or {}
    return (entrada.get("data") or {}) if entrada.get("success") else None


def por_que_sin_precio(ficha):
    """Por que un juego que existe no tiene precio.

    Son dos cosas distintas y la ficha las distingue sola, asi que no hay nada
    que adivinar: si coming_soon es cierto todavia no esta a la venta, y si no,
    es que Steam ha dejado de venderlo. A Horizon Zero Dawn Complete Edition le
    paso al salir la Remastered: conserva sus 'packages' pero ya no tiene
    precio.
    """
    lanzamiento = (ficha or {}).get("release_date") or {}
    return PROXIMAMENTE if lanzamiento.get("coming_soon") else RETIRADO


# --------------------------------------------------------------------------
# Las ediciones especiales
# --------------------------------------------------------------------------
#
# Salen de 'package_groups' de la propia ficha, o sea de las opciones de compra
# del juego. Un DLC no esta ahi: es otra app, con su 'type': 'dlc'. Aun asi
# Steam cuelga de ese sitio tres cosas que no son ediciones, y las tres se
# descartan abajo.
#
# La regla es EXIGIR un termino de edicion, no descartar lo que suene mal, que
# es lo mismo que decidio el bloque 'tema' de medios.json y por el mismo
# motivo: una lista de lo que sobra deja pasar todo lo que no nombra. Medido
# sobre las 74 opciones de compra de los 50 juegos del catalogo el 18-09-2026,
# el filtro acepta 17 ediciones sin un solo falso positivo ni falso negativo.

EDICION = ["edition", "edicion", "deluxe", "premium", "complete", "completa",
           "definitive", "definitiva", "ultimate", "goty", "game of the year",
           "gold", "legendaria", "legendary", "collection", "coleccion"]

# Lo que Steam cuelga junto a las ediciones y no lo es. 'Commercial License' es
# la licencia para negocios (UNCHARTED y los dos Spider-Man la tienen) y los
# 'DLC Pack' son justo lo que no se quiere aqui (Persona 3 Reload, Persona 5
# Tactica). Gana a la lista de arriba porque 'Legacy of Thieves Collection -
# Commercial License' lleva las dos cosas.
NO_ES_EDICION = ["commercial license", "licencia comercial", "dlc",
                 "soundtrack", "banda sonora", "season pass",
                 "pase de temporada"]


def nombre_del_sub(texto):
    """El nombre de una opcion de compra, sin el precio que Steam le pega.

    El 'option_text' llega como 'Nombre - <span ...>49,99EUR</span> 19,99EUR',
    o sea con etiquetas dentro. Se quitan y se corta por el precio.
    """
    limpio = re.sub(r"<[^>]+>", "", texto or "")
    limpio = re.sub(r"\s+", " ", limpio).strip()
    return re.sub(r"\s*-\s*[\d.,]+\s*€.*$", "", limpio).strip()


def acortar(nombre, juego):
    """La edicion sin repetir delante (ni detras) el nombre del juego.

    En ingles el juego va delante ('ELDEN RING Shadow of the Erdtree Edition')
    y en espanol detras ('Edicion Completa de Stellar Blade'), asi que hay que
    mirar por los dos lados o la mitad de los nombres salen duplicados.
    """
    suyo, entero = plano(juego), plano(nombre)
    if entero.startswith(suyo):
        resto = nombre[len(juego):].lstrip(" -:·")
        if resto:
            return resto
    for union in (" de ", " of ", " "):
        if entero.endswith(union + suyo):
            resto = nombre[:len(nombre) - len(union) - len(juego)].strip(" -:·")
            if resto:
                return resto
    return nombre


def ediciones_de(ficha):
    """Las ediciones especiales de una ficha, ya filtradas y con nombre corto."""
    subs = [s for grupo in (ficha or {}).get("package_groups", [])
            for s in grupo.get("subs", [])]
    juego = (ficha or {}).get("name", "")
    fuera = []
    for sub in subs:
        # Con una sola opcion de compra, esa opcion ES el juego base, se llame
        # como se llame: Sackboy y DRAGON QUEST XI S la publican con el nombre
        # en ingles, asi que compararla con el del juego no la reconoceria.
        if len(subs) == 1:
            continue
        nombre = nombre_del_sub(sub.get("option_text"))
        if clave(nombre) == clave(juego):
            continue
        texto = plano(nombre)
        if any(t in texto for t in NO_ES_EDICION):
            continue
        # Se compara sin tildes en los dos lados, igual que el filtro 'tema' de
        # medios.json. Sin eso se perdia la 'Edicion Super Limit-Breaking NEO'
        # de DRAGON BALL, que era el unico falso negativo de la medicion.
        if not any(e in texto for e in EDICION):
            continue
        fuera.append({"nombre": acortar(nombre, juego),
                      "packageid": sub.get("packageid")})
    return fuera


# --------------------------------------------------------------------------
# La serie de precios
# --------------------------------------------------------------------------

def ruta_serie(mes):
    return SERIES / f"{mes}.json"


def leer_serie(mes):
    ruta = ruta_serie(mes)
    return leer_json(ruta) if ruta.exists() else {"mes": mes, "juegos": {}}


def anotar_serie(serie, cuando, juegos):
    """Anade a la serie los precios que hayan cambiado. Devuelve cuantos.

    Solo los cambios, por lo mismo que en precios.py: un precio vale hasta el
    punto siguiente, asi que la serie es escalonada por definicion y guardar
    una entrada por pasada repetiria catorce veces el mismo numero.
    """
    dentro = serie.setdefault("juegos", {})
    nuevos = 0
    for juego in juegos:
        por_edicion = dentro.setdefault(juego["id"], {})
        for edicion in juego.get("ediciones", []):
            if edicion.get("estado") != OK or edicion.get("precio") is None:
                continue
            puntos = por_edicion.setdefault(edicion["nombre"], [])
            if puntos and puntos[-1]["precio"] == edicion["precio"]:
                continue
            puntos.append({"cuando": cuando, "precio": edicion["precio"]})
            nuevos += 1
    return nuevos


# --------------------------------------------------------------------------
# consultar
# --------------------------------------------------------------------------

def previos():
    """Lo publicado en la pasada anterior, por juego y edicion.

    De aqui salen el minimo historico, la fecha en que se vio y el precio con
    el que se compara para saber si algo ha bajado.
    """
    if not SALIDA.exists():
        return {}
    fuera = {}
    for juego in leer_json(SALIDA).get("juegos", []):
        fuera[juego.get("id")] = {e.get("nombre"): e
                                  for e in juego.get("ediciones", [])}
    return fuera


def registrar(nombre, precio, anterior, ahora, enlace, packageid=None):
    """Un registro de precio listo para publicar, con su minimo y su bajada."""
    anterior = anterior or {}
    registro = {
        "nombre": nombre,
        "packageid": packageid,
        "enlace": enlace,
        "moneda": MONEDA,
    }

    if precio is None:
        # No ha entrado ahora: se conserva el anterior diciendolo, o se marca
        # como nuevo si es la primera vez. Borrarlo dejaria un hueco donde
        # antes habia un dato bueno.
        if anterior.get("precio") is None:
            registro.update({"precio": None, "base": None, "descuento": 0,
                             "estado": anterior.get("estado") or NUEVO,
                             "consultado": anterior.get("consultado")})
        else:
            registro.update({
                "precio": anterior.get("precio"), "base": anterior.get("base"),
                "descuento": anterior.get("descuento") or 0, "estado": VIEJO,
                "consultado": anterior.get("consultado")})
        for campo in ("minimo", "minimo_fecha"):
            if anterior.get(campo) is not None:
                registro[campo] = anterior[campo]
        return registro

    registro.update({
        "precio": precio["precio"],
        "base": precio["base"],
        "descuento": precio["descuento"],
        "estado": OK,
        "consultado": ahora.strftime(FORMATO_FECHA_HORA),
    })

    minimo, cuando = anterior.get("minimo"), anterior.get("minimo_fecha")
    if minimo is None or precio["precio"] < minimo:
        minimo, cuando = precio["precio"], ahora.strftime(FORMATO_FECHA)
    registro["minimo"] = minimo
    registro["minimo_fecha"] = cuando

    # Ha bajado desde la ultima vez que se miro. Es lo que se viene a ver, asi
    # que se deja dicho en el propio registro y la web no tiene que adivinarlo.
    antes = anterior.get("precio")
    if antes is not None and antes > precio["precio"]:
        registro["bajada"] = {"desde": antes}

    return registro


def cmd_consultar(args):
    _, catalogo = leer_catalogo()
    ahora = datetime.now(ESPANA)
    anteriores = previos()

    try:
        precios = precios_de_juegos([j["appid"] for j in catalogo])
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as error:
        print(f"ERROR: la API de Steam no responde ({error}). Sin ella no hay "
              "nada que publicar, asi que no se toca data/steam.json.")
        return 1

    juegos, con_precio, sin_ficha = [], 0, []
    for entrada in catalogo:
        appid = entrada["appid"]
        ident = entrada.get("id") or identificador(entrada.get("nombre", ""))
        antes = anteriores.get(ident, {})
        ediciones = []

        # La edicion estandar: el juego a secas. Va siempre la primera porque
        # es la que se ve con el bloque plegado.
        if appid in precios:
            precio = precios[appid]
            if precio is None:
                # Existe pero no esta a la venta. Cuesta una peticion mas saber
                # por que, y solo la pagan los pocos que estan en ese caso.
                ficha = ficha_completa(appid)
                registro = registrar("Estandar", None, antes.get("Estandar"),
                                     ahora, FICHA.format(appid))
                registro["estado"] = por_que_sin_precio(ficha)
                registro["precio"] = registro["base"] = None
                time.sleep(PAUSA)
            else:
                registro = registrar("Estandar", precio, antes.get("Estandar"),
                                     ahora, FICHA.format(appid))
                con_precio += 1
        else:
            sin_ficha.append(entrada.get("nombre") or appid)
            registro = registrar("Estandar", None, antes.get("Estandar"),
                                 ahora, FICHA.format(appid))
        ediciones.append(registro)

        for edicion in entrada.get("ediciones", []):
            packageid = edicion.get("packageid")
            try:
                precio = precio_de_edicion(packageid)
            except ValueError as error:
                print(f"ERROR: {error}")
                return 1
            except (urllib.error.HTTPError, urllib.error.URLError, OSError):
                precio = None
            ediciones.append(registrar(
                edicion.get("nombre", "Edicion especial"), precio,
                antes.get(edicion.get("nombre")), ahora,
                FICHA_PACK.format(packageid), packageid))
            if precio is not None:
                con_precio += 1
            time.sleep(PAUSA)

        juegos.append({
            "id": ident,
            "nombre": entrada.get("nombre", ""),
            "appid": appid,
            "enlace": FICHA.format(appid),
            "ediciones": ediciones,
        })

    if sin_ficha:
        print(f"AVISO: la API no reconoce la ficha de {len(sin_ficha)} juegos: "
              f"{', '.join(str(x) for x in sin_ficha)}. Se conserva su ultimo "
              "precio. Si se repite, comprueba el appid en la tienda: puede "
              "que el juego haya cambiado de ficha.")

    if con_precio < MINIMO_PARA_PUBLICAR:
        print(f"ERROR: no ha entrado ni un precio de {len(catalogo)} juegos. "
              "Eso no es que los juegos no esten a la venta, es que la API no "
              "esta respondiendo como se espera. No se toca data/steam.json "
              "para no marcar todo el catalogo como viejo sin haber mirado.")
        return 1

    escribir_json(SALIDA, {
        "seccion": "steam",
        "actualizado": ahora.strftime(FORMATO_FECHA_HORA),
        "juegos": juegos,
    })

    mes = ahora.strftime("%Y-%m")
    serie = leer_serie(mes)
    nuevos = anotar_serie(serie, ahora.strftime(FORMATO_FECHA_HORA), juegos)
    if nuevos:
        SERIES.mkdir(parents=True, exist_ok=True)
        escribir_json(ruta_serie(mes), serie)

    rebajados = sum(1 for j in juegos for e in j["ediciones"]
                    if e.get("estado") == OK and e.get("descuento"))
    print(f"{len(juegos)} juegos, {con_precio} precios, {rebajados} rebajados. "
          f"{nuevos} cambios anotados en la serie de {mes}.")
    return 0


# --------------------------------------------------------------------------
# descubrir y probar
# --------------------------------------------------------------------------

def cmd_descubrir(args):
    """Rellena el catalogo: nombre, id y ediciones de cada appid.

    Sirve para anadir un juego escribiendo solo su 'appid', y para revisar si
    un juego ha estrenado edicion especial desde la ultima vez. No quita nada
    que ya este puesto a mano salvo que se pida con --rehacer: una edicion
    retirada de la tienda seguiria interesando como historico.
    """
    datos, catalogo = leer_catalogo()
    cambios = []

    for entrada in catalogo:
        appid = entrada["appid"]
        try:
            ficha = ficha_completa(appid)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            print(f"AVISO: no se ha podido leer la ficha de {appid} ({e}).")
            continue
        if not ficha:
            print(f"AVISO: la API no reconoce el appid {appid}. Comprueba el "
                  "numero en la URL de la ficha.")
            continue

        nombre = ficha.get("name") or entrada.get("nombre", "")
        if entrada.get("nombre") != nombre:
            cambios.append(f"{appid}: nombre -> {nombre}")
            entrada["nombre"] = nombre
        if not entrada.get("id"):
            entrada["id"] = identificador(nombre)
            cambios.append(f"{appid}: id -> {entrada['id']}")

        halladas = ediciones_de(ficha)
        if args.rehacer:
            tiene = []
        else:
            tiene = entrada.get("ediciones", [])
        conocidos = {e.get("packageid") for e in tiene}
        for edicion in halladas:
            if edicion["packageid"] not in conocidos:
                tiene.append(edicion)
                cambios.append(f"{appid}: edicion -> {edicion['nombre']}")
        if tiene:
            entrada["ediciones"] = tiene
        time.sleep(PAUSA)

    if not cambios:
        print("El catalogo ya estaba al dia: nada que anadir.")
        return 0

    for linea in cambios:
        print(f"  {linea}")
    if args.probar:
        print(f"\n{len(cambios)} cambios. Con --probar no se ha escrito nada.")
        return 0

    datos["juegos"] = catalogo
    escribir_json(CATALOGO, datos)
    print(f"\n{len(cambios)} cambios escritos en {CATALOGO.name}.")
    return 0


def cmd_probar(args):
    """Una ficha suelta, para homologar un juego antes de meterlo al catalogo."""
    try:
        appid = int(args.appid)
    except ValueError:
        print(f"ERROR: '{args.appid}' no es un appid. Es el numero de la URL "
              "de la ficha: store.steampowered.com/app/1245620/...")
        return 1

    ficha = ficha_completa(appid)
    if not ficha:
        print(f"ERROR: la API no reconoce el appid {appid}.")
        return 1

    print(f"nombre     {ficha.get('name')}")
    print(f"tipo       {ficha.get('type')}")
    lanzamiento = ficha.get("release_date") or {}
    print(f"lanzado    {lanzamiento.get('date')}"
          f"{'  (todavia no a la venta)' if lanzamiento.get('coming_soon') else ''}")

    precio = de_precio(ficha.get("price_overview"))
    if precio:
        rebaja = f"  (-{precio['descuento']}%)" if precio["descuento"] else ""
        print(f"precio     {precio['precio']:.2f} {precio['moneda']}"
              f"   antes {precio['base']:.2f}{rebaja}")
    else:
        print(f"precio     no tiene: {por_que_sin_precio(ficha)}")

    ediciones = ediciones_de(ficha)
    print(f"ediciones  {len(ediciones)}")
    for edicion in ediciones:
        suelto = precio_de_edicion(edicion["packageid"])
        importe = f"{suelto['precio']:.2f} {suelto['moneda']}" if suelto else "?"
        print(f"    {edicion['packageid']}  {importe:>14}  {edicion['nombre']}")
        time.sleep(PAUSA)

    print("\nPara el catalogo:")
    bloque = {"id": identificador(ficha.get("name", "")),
              "nombre": ficha.get("name"), "appid": appid}
    if ediciones:
        bloque["ediciones"] = ediciones
    print(json.dumps(bloque, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------
# frescura: la pasada de hoy, ha salido?
# --------------------------------------------------------------------------
#
# Mismo planteamiento que precios.py, y por el mismo caso real: un cron que no
# dispara NO falla, asi que nadie se entera. Las horas van en UTC porque es lo
# que ponen los cron, no en la hora espanola de su comentario: si se escriben
# en local, medio ano funciona y el otro medio da una falsa alarma cada manana.

HORAS_PASADA_UTC = [(5, 20), (13, 20)]

# Retraso perdonado. GitHub no dispara los cron a su hora nunca, y desde el
# 15-09-2026 el retraso medido no son 40 minutos sino unas cuatro horas y
# media, todos los dias. Con 2 h esto seguiria avisando a diario de algo que
# no es una averia, asi que se le da el mismo margen que ya se le da de hecho.
MARGEN_PASADA = 5


def pasada_exigible(ahora, margen=None):
    """La ultima pasada que ya tenia que haber salido, o None si ninguna.

    Se compara contra un horario FIJO y no contra la antiguedad de la anterior.
    La diferencia no es cosmetica: medir la antiguedad hace que cuanto mas se
    retrase GitHub, mas reciente parezca la pasada que se ha perdido, y el
    mismo fallo que hay que cazar desactiva al que lo caza.
    """
    margen = MARGEN_PASADA if margen is None else margen
    limite = ahora.astimezone(timezone.utc) - timedelta(hours=margen)
    candidatas = []
    for dia in (0, 1):
        cuando = (limite - timedelta(days=dia)).date()
        for hora, minuto in HORAS_PASADA_UTC:
            momento = datetime.combine(cuando, hora_del_dia(hora, minuto),
                                       tzinfo=timezone.utc)
            if momento <= limite:
                candidatas.append(momento)
    return max(candidatas) if candidatas else None


def cmd_frescura(args, escribir=print):
    if not SALIDA.exists():
        escribir(f"ERROR: no existe {SALIDA.relative_to(RAIZ)}. Lanza "
                 "'python3 scripts/steam.py consultar'.")
        return 1

    ahora = datetime.now(ESPANA)
    exigible = pasada_exigible(ahora, args.margen)
    if exigible is None:
        escribir("Todavia no ha vencido ninguna pasada de hoy.")
        return 0

    cuando = leer_json(SALIDA).get("actualizado")
    try:
        ultima = datetime.strptime(cuando, FORMATO_FECHA_HORA).replace(
            tzinfo=ESPANA)
    except (TypeError, ValueError):
        escribir(f"ERROR: data/steam.json tiene un 'actualizado' que no se "
                 f"entiende ({cuando!r}).")
        return 1

    # Con el dia y no solo la hora: el margen hace que la pasada exigible pueda
    # ser la de ayer por la tarde, y "las 15:20" a secas se lee como la de hoy.
    toca = exigible.astimezone(ESPANA).strftime("%H:%M del %d-%m-%Y")

    if ultima.astimezone(timezone.utc) >= exigible:
        escribir(f"La pasada de las {toca} esta hecha: {cuando}.")
        return 0

    horas = (ahora - ultima).total_seconds() / 3600
    escribir(f"AVISO: falta la pasada de Steam de las {toca}. Lo ultimo "
             f"publicado es de {cuando}, hace {horas:.1f} h. Un cron que no "
             "dispara no falla, asi que esto no sale en ningun log: lanza "
             "'Steam' a mano desde Actions.")
    return 1


def revisar_frescura():
    """(ok, lineas) sin imprimir nada, para que 'noticias.py vigilar' lo use."""
    lineas = []
    codigo = cmd_frescura(argparse.Namespace(margen=MARGEN_PASADA),
                          lineas.append)
    return codigo == 0, lineas


# --------------------------------------------------------------------------

def main():
    partes = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ordenes = partes.add_subparsers(dest="orden", required=True)

    ordenes.add_parser("consultar", help="consulta los precios y publica el JSON")

    descubrir = ordenes.add_parser(
        "descubrir", help="rellena nombre, id y ediciones del catalogo")
    descubrir.add_argument("--probar", action="store_true",
                           help="ensena lo que cambiaria sin tocar el fichero")
    descubrir.add_argument("--rehacer", action="store_true",
                           help="rehace las ediciones en vez de solo anadir")

    probar = ordenes.add_parser("probar", help="una ficha suelta, sin publicar")
    probar.add_argument("appid")

    frescura = ordenes.add_parser("frescura", help="ha salido la pasada de hoy?")
    frescura.add_argument("--margen", type=float, default=None,
                          help="horas de retraso perdonadas (0 = ya toca)")

    args = partes.parse_args()
    return {
        "consultar": cmd_consultar,
        "descubrir": cmd_descubrir,
        "probar": cmd_probar,
        "frescura": cmd_frescura,
    }[args.orden](args)


if __name__ == "__main__":
    sys.exit(main())
