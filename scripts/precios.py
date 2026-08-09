#!/usr/bin/env python3
"""Precios de la seccion de Ofertas.

Consulta las fichas de scripts/productos.json y escribe data/ofertas.json. Aqui
no hay nada que decidir: el precio se lee del bloque Product que las tiendas
incrustan en su HTML para Google, no del criterio de nadie. Por eso este paso
lo hace un script entero y la rutina solo lo lanza.

    python3 scripts/precios.py consultar
    python3 scripts/precios.py probar <url>

Solo biblioteca estandar. Comparte utilidades con noticias.py, que esta al lado.
"""

import argparse
import json
import re
import sys
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


def traer(url):
    """HTML de una ficha, decodificado con la codificacion que diga la tienda."""
    peticion = urllib.request.Request(url, headers={
        "User-Agent": AGENTE,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es-ES,es;q=0.9",
    })
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        crudo = respuesta.read()
        codificaciones = [respuesta.headers.get_content_charset(), "utf-8", "cp1252"]
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


def oferta_de(producto):
    oferta = producto.get("offers") or {}
    if isinstance(oferta, list):
        oferta = oferta[0] if oferta else {}
    return oferta if isinstance(oferta, dict) else {}


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
        oferta = oferta_de(producto)
        bruto = oferta.get("price") or oferta.get("lowPrice")
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
                precio, extra = leer_precio(traer(tienda["url"]), tienda["url"])
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

            consultados += 1
            minimo = anterior.get("minimo")
            minimo_fecha = anterior.get("minimo_fecha")
            if minimo is None or precio < minimo:
                minimo, minimo_fecha = precio, ahora.strftime(FORMATO_FECHA)

            precios.append({
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
            })
            aviso = "" if extra["elegido_por_referencia"] else "  (ojo: ficha elegida por descarte)"
            stock = " [sin stock]" if extra["disponible"] is False else ""
            print(f"{etiqueta}: {precio:.2f} {extra['moneda']}{stock}{aviso}")

        salida.append({
            "id": producto["id"],
            "nombre": producto["nombre"],
            "plataforma": producto.get("plataforma", ""),
            "precios": precios,
        })

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
    try:
        precio, extra = leer_precio(traer(args.url), args.url)
    except Exception as e:
        print(f"ERROR: no se ha podido abrir la ficha: {e}")
        return 1
    if precio is None:
        print(f"ERROR: {extra}. Esta tienda no sirve para el catalogo.")
        return 1
    print(f"Ficha    : {extra['nombre_ficha']}")
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
    p.set_defaults(func=cmd_probar)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
