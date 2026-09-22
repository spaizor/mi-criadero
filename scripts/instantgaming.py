#!/usr/bin/env python3
"""El precio de un juego en Instant Gaming, para la seccion de Steam.

POR QUE ESTA TIENDA Y NINGUNA OTRA DEL MERCADO GRIS

Se sondearon las seis el 22-09-2026 y solo esta deja entrar. Kinguin, G2A,
Gamivo y CDKeys responden 403 con un reto de Cloudflare EN LA PORTADA, que es
el corte que este proyecto ya fijo con gg.deals: ahi ya no es el modo de pedir,
es una deteccion, y saltarsela es el lado equivocado del limite que se puso con
Amazon. Sus APIs (gateway.kinguin.net, api.g2a.com) devuelven un 401 limpio, o
sea que la puerta existe, pero pide cuenta de revendedor o de afiliado, que es
una decision del usuario y no una cuestion tecnica.

Eneba se cayo por otro motivo, y es el que importa aqui: su ficha SI se abre,
pero el precio solo aparece con navegador y ademas lo publica con un "No es el
precio final" al lado, porque es un mercado de revendedores que suma
comisiones al pagar. Publicar ese numero seria mentir en el precio, que es lo
unico que esta seccion no puede hacer.

Instant Gaming no tiene nada de eso: responde a urllib, sirve el precio ya
hecho en el HTML y lo hace en euros.

    <meta itemprop="priceCurrency" content="EUR" />
    <meta itemprop="price" content="0.99" data-price-eur="0.99" />

O sea el mismo bloque schema.org que lee precios.py en las tiendas de Ofertas,
pero sin necesitar Chromium. Su robots.txt no prohibe automatizar: tapa el
carrito, la cuenta y el buscador, y deja las fichas abiertas.

POR QUE EL CATALOGO LLEVA EL ID ESCRITO

Porque su buscador esta en 'Disallow: /es/busquedas/' y no publican sitemap
(probado: /sitemap.xml da 404), asi que no hay forma permitida de preguntarle
"cual es la ficha de este juego". El id se resuelve UNA VEZ y se congela en
scripts/juegos-steam.json, igual que el 'itad' y por el mismo motivo.

Del id sale la URL sola, porque el slug NO cuenta: medido el 22-09-2026,
/es/12335-x/ devuelve 200 y la misma ficha que la URL larga. Aun asi lo que se
publica es el enlace canonico que trae la propia pagina, no el inventado.

LO QUE SE RECHAZA, Y POR QUE NO ES UNA MANIA

Instant Gaming vende tres cosas que no son "este juego en Steam mas barato", y
las tres se distinguen leyendo la ficha y no adivinando:

  - Claves de OTRA plataforma (GOG, Ubisoft, EA, Microsoft Store). Es el mismo
    filtro que ya aplica itad.py, y aqui hace mas falta todavia: al buscar
    Cyberpunk 2077 lo primero que aparece es su version de GOG.
  - Claves de OTRA REGION. Vende la misma edicion con clave de Latin America,
    que no se activa en Espana. Lo dice el propio titulo de la ficha
    ("... - PC (Steam) - Latin America"), asi que no hay que deducirlo.
  - Fichas que no son de PC (Switch, PS5), que salen del mismo catalogo.

La region se comprueba con LISTA BLANCA y no descartando las malas, que es la
regla que este proyecto ya aprendio con el bloque 'tema' de medios.json: una
lista de regiones prohibidas deja pasar la que no se te haya ocurrido, y el
precio de una clave que no puedes activar es peor que no tener precio.
"""

import gzip
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

# La ficha en espanol, que es la que da los precios en euros. El '-x' es el
# slug de relleno: la tienda lo ignora y solo mira el numero.
FICHA = "https://www.instant-gaming.com/es/{}-x/"

TIENDA = "Instant Gaming"
MONEDA = "EUR"

# Las mismas que itad.py, y a proposito: lo que el usuario compra no cambia
# segun de donde venga el precio. Se compara en minusculas.
PLATAFORMAS = {"steam", "epic games", "epic"}

# Solo fichas de ordenador. La tienda vende tambien Switch y PlayStation, y
# esas son otro producto, no este juego mas barato.
DISPOSITIVOS = {"pc", "pc & mac", "pc y mac", "mac"}

# Regiones que SI se activan desde Espana. Una ficha sin sufijo de region es
# una clave sin restriccion, que es el caso normal. Ver el docstring: esto es
# lista blanca por decision, no por pereza.
#
# Se compara TROZO A TROZO partiendo por '&', porque la tienda escribe tambien
# regiones compuestas: "Europe & USA & Canada" es una clave que vale en las
# tres, asi que vale aqui, mientras que "USA & Canada" no. Comparar la cadena
# entera contra la lista habria tirado la de Tales of Graces f, que es de las
# buenas, y esa es justo la clase de fallo silencioso que no se ve: un juego
# que simplemente deja de tener precio.
REGIONES = {"europe", "europa", "global", "worldwide", "emea", "eu", "spain",
            "espana"}

INTENTOS = 3
ESPERA_REINTENTO = 3
TIEMPO = 30

# Entre fichas. Aqui son unas cuantas decenas de peticiones a una sola tienda y
# dos veces al dia, asi que la pausa no es cosmetica: es la diferencia entre
# una visita y una rafaga. Es el mismo motivo que PAUSA_MISMA_TIENDA en
# precios.py.
PAUSA = 1.5

AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


class FichaRara(ValueError):
    """La ficha se ha abierto pero no es la que esta seccion publica."""


class SinExistencias(FichaRara):
    """La ficha es la buena, pero hoy no hay nada que comprar.

    Va aparte porque NO es un aviso: que una tienda de claves se quede sin
    existencias es un estado normal del dia a dia, y sacarlo en el parte de
    cada pasada hasta que repongan es el aviso que sale siempre y se deja de
    leer. Lo que se hace es no publicar la fila, y vuelve sola.
    """


# --------------------------------------------------------------------------
# Descarga
# --------------------------------------------------------------------------

def descargar(url):
    """El HTML de una ficha, reintentando solo los cortes de red.

    Un codigo HTTP es una respuesta y no un corte, igual que en steam.py: si
    empiezan a dar 403 hay que enterarse, no insistir tres veces.

    Se mira el numero magico del gzip y no la cabecera porque no todos la
    mandan bien; es la leccion de Vandal, que estuvo meses dado por bloqueado
    cuando lo unico que pasaba es que comprimia sin que se lo pidieran.
    """
    peticion = urllib.request.Request(url, headers={
        "User-Agent": AGENTE,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es-ES,es;q=0.9",
    })
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
    if crudo[:2] == b"\x1f\x8b":
        crudo = gzip.decompress(crudo)
    return crudo.decode("utf-8", "replace")


# --------------------------------------------------------------------------
# Leer la ficha
# --------------------------------------------------------------------------

def _texto(patron, pagina, defecto=None):
    encontrado = re.search(patron, pagina, re.S)
    return html.unescape(encontrado.group(1)).strip() if encontrado else defecto


def migas(pagina):
    """['PC', 'Steam', 'Nombre del juego'] del BreadcrumbList de la ficha.

    El nombre sale de aqui y no del titulo porque el titulo lo trae envuelto
    ("Comprar X - PC (Steam)") y hay juegos cuyo nombre lleva guiones dentro,
    asi que recortarlo seria adivinar donde acaba.
    """
    for bloque in re.findall(
            r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
            pagina, re.S):
        try:
            datos = json.loads(bloque)
        except ValueError:
            continue
        if datos.get("@type") != "BreadcrumbList":
            continue
        return [paso.get("item", {}).get("name") or paso.get("name") or ""
                for paso in datos.get("itemListElement", [])]
    return []


def region_del_titulo(titulo):
    """La region de la clave, o None si la ficha no pone ninguna.

    El titulo es "Comprar <juego> - <dispositivos> (<plataforma>)" y, cuando la
    clave esta limitada, anade " - <region>" detras del parentesis. Se lee ahi
    y no en el cuerpo de la pagina porque ahi es un dato y no un adorno.
    """
    resto = re.search(r"\)\s*-\s*(.+?)\s*$", titulo or "")
    return resto.group(1) if resto else None


def vale_la_region(region):
    """Si una clave de esa region se activa desde Espana.

    Se parte por '&' y basta con que UN trozo este en la lista blanca: en
    "Europe & USA & Canada" la clave vale en las tres, asi que vale aqui;
    "USA & Canada" no tiene ningun trozo bueno y se cae. Comparar la cadena
    entera habria tirado la primera, que es de las buenas.
    """
    return any(trozo.strip().lower() in REGIONES
               for trozo in re.split(r"[&+/]", region or ""))


def numero(texto):
    """El importe de un trozo de HTML como '13 &nbsp;EUR' o '0.99', o None."""
    if not texto:
        return None
    limpio = re.sub(r"[^0-9,.]", "", html.unescape(texto))
    if not limpio:
        return None
    # La tienda mezcla los dos separadores en la misma ficha: el precio del
    # bloque schema.org viene con punto ("0.99") y el tachado de al lado con
    # coma ("52,99"). Se mira cual va el ultimo en vez de elegir uno.
    if "," in limpio and limpio.rfind(",") > limpio.rfind("."):
        limpio = limpio.replace(".", "").replace(",", ".")
    else:
        limpio = limpio.replace(",", "")
    try:
        return round(float(limpio), 2)
    except ValueError:
        return None


def leer(pagina, identificador):
    """La oferta de una ficha, en el mismo formato que publica itad.py.

    Devuelve el bloque tal cual lo espera data/steam.json, para que la web no
    tenga que distinguir de donde vino cada fila. Lo unico que no se rellena
    son los campos que solo sabe ITAD (marca, minimo de la tienda, caducidad):
    van a None a proposito, que es lo que la web ya trata como "no lo se".

    Levanta FichaRara cuando la ficha no es de este juego en Steam para
    Espana. Es un error y no un None porque quien llama tiene que poder
    decirlo en el parte: una ficha descartada en silencio es un precio que
    desaparece sin que nadie sepa por que.
    """
    pasos = migas(pagina)
    if len(pasos) < 3:
        raise FichaRara(
            "la ficha no trae el bloque de migas de pan, que es de donde salen "
            "el nombre y la plataforma. O ha cambiado la pagina, o lo que ha "
            "llegado no es una ficha de producto")

    dispositivo, plataforma, nombre = pasos[0], pasos[1], pasos[-1]
    if dispositivo.strip().lower() not in DISPOSITIVOS:
        raise FichaRara(
            f"es una ficha de {dispositivo}, no de PC. Instant Gaming vende el "
            "mismo juego para consola con el mismo nombre, asi que el id del "
            "catalogo apunta al producto equivocado")
    if plataforma.strip().lower() not in PLATAFORMAS:
        raise FichaRara(
            f"la clave es de {plataforma} y esta seccion publica Steam y Epic. "
            "Es el filtro de plataforma de itad.py: una copia que no vas a "
            "usar no es el mismo juego mas barato")

    titulo = _texto(r'property="og:title"[^>]*content="([^"]*)"', pagina, "")
    region = region_del_titulo(titulo)
    if region is not None and not vale_la_region(region):
        raise FichaRara(
            f"la clave es de la region '{region}', que no se activa desde "
            "Espana. Busca en la tienda la version sin region o la de Europe")

    # LA MONEDA LA ELIGE LA IP, NO LA URL, y esto se vio en el primer run del
    # runner: pedir /es/ pone la ficha en espanol pero el precio salia en USD
    # porque GitHub corre en Estados Unidos, y los 43 juegos se cayeron de
    # golpe. Es el mismo fallo que ya evitan el 'cc=es' de steam.py y el
    # 'country=ES' de itad.py, con el agravante de que aqui no hay parametro
    # que valga: el de la tienda ('?currency=') esta en su robots.txt.
    #
    # La salida la da la propia ficha, que publica los dos numeros:
    #
    #     <meta itemprop="price" content="3.19" data-price-eur="3.19" />
    #
    # 'content' es lo que se ensena y cambia con la IP; 'data-price-eur' es
    # SIEMPRE euros. Se ve mejor en los listados de la misma pagina, donde van
    # en pareja ('data-price' junto a 'data-price-eur'), y lo confirma la tabla
    # de cambio que la ficha lleva dentro: la tienda guarda el precio en euros
    # y convierte al pintar. O sea que esto no es una conversion nuestra -que
    # es lo que hace a una tienda de ITAD no publicable- sino el precio de
    # tarifa leido donde lo escribe la tienda.
    moneda = _texto(r'itemprop="priceCurrency"[^>]*content="([^"]*)"', pagina)
    en_euros = moneda == MONEDA

    precio = numero(
        _texto(r'itemprop="price"[^>]*data-price-eur="([^"]*)"', pagina))
    if precio is None and en_euros:
        precio = numero(
            _texto(r'itemprop="price"[^>]*content="([^"]*)"', pagina))
    if precio is None:
        raise FichaRara(
            "la ficha no trae precio en euros. Si tampoco trae "
            f"'data-price-eur' y la pagina viene en {moneda}, es que la tienda "
            "ha cambiado como publica el precio: hay que mirar la ficha antes "
            "de tocar nada, porque el numero que se ve NO es el de euros. Si "
            "viene en euros, suele ser un juego anunciado y todavia no a la "
            "venta, o uno que la tienda ha dejado de vender")

    disponible = _texto(r'itemprop="availability"[^>]*content="([^"]*)"', pagina)

    # SIN EXISTENCIAS SE PUBLICA COMO 0,00 EUR, y esto hay que atajarlo aqui.
    # Medido el 22-09-2026 con Mewgenics: la tienda declara 'OutOfStock' y
    # ademas deja el meta del precio en "0.00", sin bloque de tachado ni de
    # rebaja. O sea que el numero tiene la forma del campo bueno y no lo es,
    # igual que la cuota de Orange en precios.py, con el agravante de que un
    # 0,00 EUR en la web se lee como "gratis" y es lo mas barato de la lista:
    # coronaria la fila y mandaria a una ficha donde no se puede comprar.
    #
    # Se cae aqui y no se publica con una etiqueta de "agotado" porque esta
    # seccion compara precios: una fila sin precio que se puede comprar no
    # aporta nada, y las tiendas de ITAD tampoco se publican cuando no lo
    # traen. Vuelve sola en cuanto la tienda reponga.
    if precio == 0 or (disponible and "OutOfStock" in disponible):
        raise SinExistencias(
            "la tienda no tiene existencias y por eso publica el precio como "
            "0,00 EUR. No es una oferta: es el hueco donde va el precio, y "
            "publicarlo lo coronaria como el mas barato del juego")
    # El tachado NO tiene gemelo en euros: es texto pintado en la moneda de la
    # pagina. Asi que fuera de Espana se publica sin el, y no pasa nada,
    # porque la web ya solo dibuja el 'antes' cuando existe y es mayor que el
    # precio. Reconstruirlo del descuento seria un numero calculado por
    # nosotros, o sea lo que en Ofertas obliga a la etiqueta de 'estimado',
    # y no merece la pena por un precio tachado.
    #
    # El descuento si vale siempre: un porcentaje no tiene moneda.
    base = (numero(_texto(r'<div class="retail">(.*?)</div>', pagina))
            if en_euros else None)
    rebaja = _texto(r'<div class="discounted">\s*-?(\d{1,2})%', pagina)

    return {
        "tienda": TIENDA,
        "precio": precio,
        # Puede ser None, igual que el 'regular' de itad.py cuando la tienda no
        # declara tarifa. La web lo trata bien: no pinta el tachado y ya.
        "base": base,
        "descuento": int(rebaja) if rebaja else 0,
        "plataforma": plataforma,
        "cupon": None,
        "marca": None,
        "minimo_tienda": None,
        "caduca": None,
        "enlace": (_texto(r'itemprop="url"[^>]*content="([^"]*)"', pagina)
                   or FICHA.format(identificador)),
        "nombre_en_tienda": nombre,
        "disponible": bool(disponible and "InStock" in disponible),
    }


def ficha(identificador):
    """La oferta de un id de Instant Gaming."""
    return leer(descargar(FICHA.format(identificador)), identificador)


# --------------------------------------------------------------------------
# La pasada
# --------------------------------------------------------------------------

def ofertas_de(catalogo, pausa=PAUSA, escribir=None):
    """({id del juego: oferta}, [avisos]) para los juegos con 'instantgaming'.

    Una peticion por juego, que es el precio de que esta tienda no tenga API.
    Por eso solo se piden los juegos que traen id en el catalogo, y no los 52.

    NUNCA levanta: devuelve los avisos para que la pasada siga. Es la misma
    regla que otras_tiendas() con ITAD, y aqui con mas motivo todavia, porque
    lo que se juega es una tienda de las diez y no la seccion entera.
    """
    salida, avisos = {}, []
    pendientes = [(j.get("id"), j.get("instantgaming"), j.get("nombre", ""))
                  for j in catalogo]
    pendientes = [p for p in pendientes if p[1]]
    for orden, (ident, suyo, nombre) in enumerate(pendientes):
        if orden:
            time.sleep(pausa)
        try:
            oferta = ficha(suyo)
        except SinExistencias:
            continue
        except FichaRara as fallo:
            avisos.append(f"{nombre}: {fallo}")
            continue
        except urllib.error.HTTPError as fallo:
            avisos.append(f"{nombre}: la ficha {suyo} responde {fallo.code}")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as fallo:
            avisos.append(f"{nombre}: no responde ({fallo})")
            continue
        salida[ident] = oferta
        if escribir:
            escribir(f"  {nombre}: {oferta['precio']:.2f} EUR")
    return salida, avisos
