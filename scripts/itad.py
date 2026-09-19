#!/usr/bin/env python3
"""Las otras tiendas de un juego, via la API de IsThereAnyDeal (ITAD).

La seccion de Steam nacio contestando "cuanto cuesta este juego en Steam".
Esto la convierte en "donde compro este juego", que es la pregunta a la que se
entra de verdad. Medido el 19-09-2026 sobre el catalogo entero: 34 de los 50
juegos con precio estan mas baratos fuera de Steam, y no por centimos (Sonic
Racing 69,99 -> 24,38; Persona 5 Tactica 59,99 -> 15,67).

POR QUE ITAD Y NO ABRIR LAS TIENDAS

Es la leccion de precios.py aplicada antes de cometer el error. Abrir la ficha
de cada tienda son 52 juegos por N tiendas con Chromium de por medio, o sea el
coste que esta seccion justamente no paga: la pasada entera de Steam son 13 s
sin instalar nada. Y las tiendas de keys grises (G2A, Kinguin, Gamivo, CDKeys)
responden 403 con un reto de Cloudflare EN LA PORTADA, que es el corte que este
proyecto ya fijo con gg.deals: ahi ya no es el modo de pedir, es una deteccion,
y saltarsela es el lado equivocado del limite que se puso con Amazon.

ITAD entra por la puerta: API oficial, documentada, con clave gratuita, su
robots.txt vacio, y un limite de 1.000 peticiones por ventana de 5 minutos
cuando aqui se gasta UNA por pasada (el endpoint de precios admite 200 juegos
de golpe). Ademas trae de serie el minimo historico, que con solo Steam tardaba
meses en valer algo.

LO QUE NO SE PUBLICA, Y POR QUE

Los tres filtros de aqui abajo no son manias: cada uno sale de una medicion
sobre este catalogo, y estan explicados en su constante. En resumen:

  - Las tiendas que no cotizan en euros, porque su precio en euros no es un
    precio sino una conversion.
  - Las plataformas que el usuario no compra (GOG, DRM-Free, Microsoft Store).
  - La propia Steam, que ya tiene su precio en 'ediciones' y mas fresco.

No tiene comandos propios: lo usa scripts/steam.py. Solo biblioteca estandar,
como el resto del proyecto salvo precios.py.
"""

import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.isthereanydeal.com"

# El pais fija la moneda, igual que el 'cc' de Steam y por el mismo motivo: sin
# el, ITAD responde en la moneda que le parezca y el runner de GitHub puede
# estar en cualquier region. Un dolar publicado como euro no rompe nada
# visible, que es justo el fallo que este proyecto persigue, asi que ademas se
# comprueba al leer que lo que vuelve viene en EUR.
PAIS = "ES"
MONEDA = "EUR"

# El endpoint de precios admite 200 ids por peticion, asi que el catalogo
# entero (52) cabe en una. El numero va atado a ESE endpoint.
POR_LOTE = 200

INTENTOS = 3
ESPERA_REINTENTO = 3
TIEMPO = 40

# Entre peticiones sueltas, que solo son las de 'descubrir'. La de precios es
# una sola y no pausa nada.
PAUSA = 0.15


# --------------------------------------------------------------------------
# Los tres filtros
# --------------------------------------------------------------------------

# Tiendas que NO cotizan en euros. ITAD convierte su precio y lo entrega con
# 'currency: EUR', asi que la unica forma de cazarlas es mirando el numero:
# medido el 19-09-2026, el ratio de su precio de tarifa contra el de Steam es
# CONSTANTE (WinGameStore y GamesPlanet US, 0,871 en 25 y 23 juegos con
# desviacion 0,015: el cambio dolar-euro; GamesPlanet UK, 0,976: libras).
# Todas las demas dan exactamente 1,000.
#
# O sea que su "24,38 EUR" no es un precio que vayas a pagar: pagas en dolares
# y el cambio lo pone tu banco. Es el caso de la cuota de Orange otra vez, un
# numero impecable de forma que no es el precio.
#
# Quitarlas cuesta menos de lo que parece, y por eso se quitan en vez de
# etiquetarlas: WinGameStore salia como la mas barata 18 de 50 veces, pero al
# excluirla siguen siendo los MISMOS 34 juegos mas baratos fuera de Steam y el
# ahorro total solo baja de 454,71 a 412,82 EUR, un 9%. Las tiendas en euros
# estan justo detras, a centimos. Asi la seccion entera va en euros de verdad y
# no lleva una sola etiqueta de "estimado".
#
# GamesPlanet ademas esta fuera entera por decision del usuario: no tiene
# tienda espanola.
#
# COMO SE AUDITA ESTA LISTA, que hace falta porque el ratio contra Steam solo
# caza a las que convierten con un margen fijo: mirar los CENTIMOS de la tarifa
# ('base'). Una tienda que cobra en euros pone precios de escaparate y acaba
# en .99, .95, .49 o .00 practicamente siempre; una que convierte da centimos
# arbitrarios. Medido el 19-09-2026 sobre las 263 ofertas publicadas:
#
#     Fanatical, Humble, GMG, GamersGate, GameBillet...   100% redondas
#     Muve                                                 62%  (46,29 / 53,57)
#     Zapagames                                             0%  (25,03 / 30,04)
#     Fortuna Digital                                       0%  (26,13)
#
# Los 26,13 de Fortuna Digital son exactamente 29,99 USD x 0,871, o sea el
# mismo dolar que WinGameStore. Las tres se van por eso, y cuesta nada: son 11
# ofertas de 263 y solo un juego pierde su mejor precio, ELDEN RING, por diez
# centimos (50,89 en Muve -> 50,99 en GamersGate).
#
# La lista se queda escrita a mano en vez de aplicar la regla de los centimos
# en el codigo, y es a proposito: una lista no puede equivocarse, y un filtro
# automatico por centimos tiraria en silencio una oferta buena el dia que una
# tienda ponga un precio raro de verdad. Es lo mismo que decidio 'excluir_rutas'
# frente a un filtro por palabras. Lo que si hay que hacer es repasarla con la
# cuenta de arriba cuando ITAD de de alta una tienda nueva.
TIENDAS_FUERA = {
    "WinGameStore",
    "GamesPlanet FR", "GamesPlanet UK", "GamesPlanet DE", "GamesPlanet US",
    "Muve", "Zapagames", "Fortuna Digital",
}

# La tienda Steam se ignora aqui aunque ITAD la traiga, y no es un descuido: su
# precio ya esta en 'ediciones' de data/steam.json, sacado de la API de la
# propia Steam y en esta misma pasada. Publicarlo dos veces dejaria dos numeros
# para lo mismo en el mismo fichero, y el dia que discrepen -las dos consultas
# no son del mismo instante- no habria forma de saber cual manda. La web compara
# 'ediciones[0]' contra estas tiendas al pintar; no hace falta repetirlo.
TIENDA_PROPIA = "Steam"

# Las plataformas que el usuario compra. Fuera quedan GOG, DRM-Free y Microsoft
# Store: son copias que no va a usar, asi que su precio no es mas barato, es
# otra cosa.
#
# Cuesta un 12%, medido: de 34 juegos mas baratos fuera se pasa a 29 y el
# ahorro de 412,82 a 364,86 EUR. Los seis que pierden su mejor precio son cinco
# de GOG sin DRM (Kena 19,99, Little King's Story 4,49, Cult of the Lamb 11,49,
# Blasphemous 2,49, Pyre 19,49) y el Cyberpunk de Muve. Ninguno se queda sin
# ninguna oferta.
PLATAFORMAS = {"steam", "epic"}

# Y LA REGLA QUE NO SE PUEDE DESHACER SIN ROMPERLO TODO: lo que no declara
# plataforma SE CONSERVA. Medido el 19-09-2026: de las 51 ofertas sin 'drm',
# 50 son de la propia Steam, que no se molesta en declarar lo obvio. Descartar
# lo no declarado tiraria Steam entera.
#
# Y de paso es lo que cubre a Ubisoft, que el usuario si compra: "Ubisoft
# Connect" y "Uplay" NO EXISTEN como valor en ningun sitio de la API, y la
# unica oferta de Ubisoft Store (Blasphemous a 19,99 con el cupon UBI40)
# tampoco declara nada. Buscar esos nombres no habria encontrado jamas ni una.
SIN_DECLARAR_SE_QUEDA = True


# --------------------------------------------------------------------------
# Descarga
# --------------------------------------------------------------------------

class SinClave(RuntimeError):
    """No hay clave de ITAD. Se distingue de un fallo de red a proposito."""


def clave():
    """La clave de la API, del entorno. NUNCA se imprime, ni en los errores.

    Va en el entorno y no en el repositorio por lo mismo que el token de
    precios: esto es un repositorio publico. En GitHub la pone el secret
    ITAD_API_KEY del workflow; en local, la variable de entorno.
    """
    valor = (os.environ.get("ITAD_API_KEY") or "").strip()
    if not valor:
        raise SinClave(
            "falta la clave de ITAD. En GitHub la pone el secret "
            "ITAD_API_KEY (Settings -> Secrets -> Actions). En local, "
            "exportala antes de lanzar el comando. Se saca de "
            "https://isthereanydeal.com/apps/my/, apartado 'API Keys'.")
    return valor


def pedir(ruta, params=None, cuerpo=None):
    """Una llamada a la API. POST si se le pasa cuerpo, GET si no.

    La clave viaja en la CABECERA y no en la URL, aunque ITAD admita las dos
    formas. No es cosmetico: el log de Actions de un repositorio publico lo ve
    cualquiera, y basta con que una traza imprima la URL para dejar la clave
    escrita ahi para siempre. En una cabecera no puede pasar.

    Los reintentos son los de siempre en este proyecto: se repite un corte de
    red, no un codigo HTTP. Un 403 es una respuesta -clave mala, cuota agotada-
    y repetirlo tres veces llega al mismo sitio mas tarde.
    """
    params = dict(params or {})
    params.setdefault("country", PAIS)
    url = f"{API}{ruta}?" + urllib.parse.urlencode(params, doseq=True)
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None

    cabeceras = {
        "User-Agent": "Mi Criadero (https://spaizor.github.io/mi-criadero/)",
        "Accept": "application/json",
        "ITAD-API-Key": clave(),
    }
    if datos is not None:
        cabeceras["Content-Type"] = "application/json"

    peticion = urllib.request.Request(url, data=datos, headers=cabeceras)
    for intento in range(INTENTOS):
        try:
            with urllib.request.urlopen(peticion, timeout=TIEMPO) as respuesta:
                crudo = respuesta.read()
                break
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if intento == INTENTOS - 1:
                raise
            time.sleep(ESPERA_REINTENTO * (intento + 1))

    # Por si un dia comprime sin anunciarlo, como hacen Steam y Vandal. Mirar el
    # numero magico cuesta dos bytes y ahorra el rato de dar por bloqueado a
    # quien solo estaba mandando gzip.
    if crudo[:2] == b"\x1f\x8b":
        crudo = gzip.decompress(crudo)
    return json.loads(crudo.decode("utf-8"))


# --------------------------------------------------------------------------
# El id de ITAD
# --------------------------------------------------------------------------

def resolver(appid):
    """El id de ITAD de un juego de Steam, o None si no lo conoce.

    Se guarda en el catalogo y no se pregunta en cada pasada, igual que la
    lista de deseados: son 52 peticiones que devuelven siempre lo mismo.
    """
    datos = pedir("/games/lookup/v1", {"appid": appid})
    return datos["game"]["id"] if datos.get("found") else None


# --------------------------------------------------------------------------
# Precios
# --------------------------------------------------------------------------

def euros(bloque):
    """El importe de un bloque de precio, comprobando que viene en euros."""
    if not bloque:
        return None
    if bloque.get("currency") != MONEDA:
        raise ValueError(
            f"ITAD ha respondido en {bloque.get('currency')} y no en {MONEDA}. "
            f"Se pide con country={PAIS}, asi que o ha cambiado la API o la "
            "peticion ha salido sin ese parametro. No se publica nada: un "
            "dolar publicado como euro es el fallo que no se ve.")
    return bloque.get("amount")


def de_oferta(bruto):
    """Normaliza una oferta de ITAD al formato que publica la seccion.

    El precio ya lleva el cupon aplicado, comprobado el 19-09-2026 contra las
    52 ofertas con codigo: regular x (1 - cut) da el precio al centimo. Asi que
    el cupon se publica para decirlo, no para restarlo.
    """
    precio = euros(bruto.get("price"))
    if precio is None:
        return None

    # Una oferta puede traer varias plataformas (hay una con Steam y DRM-Free a
    # la vez). Se publica la primera que valga; la lista entera no aporta.
    plataformas = [d.get("name") for d in bruto.get("drm") or [] if d.get("name")]

    return {
        "tienda": (bruto.get("shop") or {}).get("name", "?"),
        "precio": precio,
        "base": euros(bruto.get("regular")),
        "descuento": bruto.get("cut") or 0,
        # None cuando la tienda no lo declara, que significa "la nativa de esta
        # tienda". La web no pinta etiqueta en ese caso en vez de inventarsela.
        "plataforma": plataformas[0] if plataformas else None,
        "cupon": bruto.get("voucher") or None,
        # 'flag' de ITAD: H minimo historico, N nuevo minimo historico,
        # S minimo de esa tienda. Son etiquetas que nos dan hechas.
        "marca": bruto.get("flag") or None,
        "minimo_tienda": euros(bruto.get("storeLow")),
        "caduca": bruto.get("expiry") or None,
        "enlace": bruto.get("url"),
    }


def vale(bruto):
    """Si esta oferta se publica: tienda en euros y plataforma que se compra."""
    tienda = (bruto.get("shop") or {}).get("name", "")
    if tienda in TIENDAS_FUERA or tienda == TIENDA_PROPIA:
        return False
    plataformas = {(d.get("name") or "").lower() for d in bruto.get("drm") or []}
    if not plataformas:
        return SIN_DECLARAR_SE_QUEDA
    return bool(plataformas & PLATAFORMAS)


def ofertas_utiles(deals):
    """Las ofertas publicables de un juego, sin repetidos y de barata a cara.

    El deduplicado es por TIENDA + PLATAFORMA y no por tienda, y la diferencia
    importa: Fanatical vende el Devil May Cry de Steam a 8,69 y el de GOG a
    25,49, y DLGamer el Persona 5 Tactica de Steam a 18,00 y el de Microsoft
    Store a 59,99. Son productos distintos, no dos precios del mismo.
    Quedarse "con el mas barato de cada tienda" juntaria los dos y haria
    parecer que hay una comparacion donde no la hay, que es lo mismo que evita
    el 'disponible: null' de Ofertas.

    Repetidos de verdad los hay -SteamWorld Heist II sale dos veces en
    Fanatical al mismo precio- y esos si se funden.
    """
    mejores = {}
    for bruto in deals or []:
        if not vale(bruto):
            continue
        oferta = de_oferta(bruto)
        if oferta is None:
            continue
        llave = (oferta["tienda"], oferta["plataforma"])
        if llave not in mejores or oferta["precio"] < mejores[llave]["precio"]:
            mejores[llave] = oferta
    return sorted(mejores.values(), key=lambda o: o["precio"])


def minimo_historico(bruto):
    """El minimo historico de ITAD, en sus tres ventanas.

    OJO: es el minimo entre TODAS las tiendas que sigue ITAD, incluidas las que
    aqui no se publican (GOG, las que cotizan en dolares). O sea que puede ser
    un precio al que este catalogo no te habria mandado nunca. Por eso se
    guarda con nombre propio y separado del 'minimo' de cada edicion, que ese
    si lo calculamos nosotros con nuestras propias pasadas.
    """
    bloque = bruto.get("historyLow") or {}
    salida = {}
    for nuestro, suyo in (("siempre", "all"), ("ano", "y1"),
                          ("trimestre", "m3")):
        valor = euros(bloque.get(suyo))
        if valor is not None:
            salida[nuestro] = valor
    return salida or None


def tiendas_de(ids):
    """{id de ITAD: {'tiendas': [...], 'minimo_itad': {...}}} para una lista.

    Una peticion por cada 200 juegos, o sea una para el catalogo entero.

      capacity=0   todas las ofertas y no solo las N primeras: el corte lo
                   ponemos nosotros con los filtros, no un tope ciego.
      nondeals     tambien las tiendas que no tienen el juego rebajado, que
                   son la mayoria y a veces las mas baratas igual.
      vouchers     que incluya las ofertas con codigo de descuento.
    """
    fuera = {}
    ids = [i for i in ids if i]
    for desde in range(0, len(ids), POR_LOTE):
        lote = ids[desde:desde + POR_LOTE]
        respuesta = pedir("/games/prices/v3",
                          {"vouchers": "true", "capacity": 0,
                           "nondeals": "true"},
                          lote)
        for bruto in respuesta:
            fuera[bruto["id"]] = {
                "tiendas": ofertas_utiles(bruto.get("deals")),
                "minimo_itad": minimo_historico(bruto),
            }
    return fuera
