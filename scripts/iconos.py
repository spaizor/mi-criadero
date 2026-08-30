#!/usr/bin/env python3
"""Genera el icono de la web en sus cinco tamanos, y la imagen de compartir.

Existe para que el icono no sea un binario opaco: los colores de las secciones
salen de assets/estilo.css, asi que el dia que cambie el acento de una seccion
se regenera con `python3 scripts/iconos.py` en vez de repintarlo a mano.

El dibujo es el criadero que da nombre a la web: un monticulo con su abertura
y, delante, un huevo por seccion con el color de esa seccion. Sin letras a
proposito: a 32 px una inicial no se lee, y una silueta con manchas de color si
se reconoce de un vistazo entre veinte pestanas.

Antes eran los cuatro colores de seccion en rejilla, y el 2x2 se rompio al
abrir geopolitica: el script se planto a proposito en vez de dejar una seccion
fuera sin decirlo, y el icono se quedo congelado con los cuatro colores viejos.
Los huevos no tienen ese problema: se reparten en dos filas y cuantos son sale
de secciones.json, asi que la sexta seccion ya no obliga a redibujar nada.

Solo biblioteca estandar, como el resto de scripts del proyecto: el PNG se
escribe a mano (zlib + struct), que para figuras planas son treinta lineas.

Y el dibujo se declara una sola vez, en formas(): de ahi salen tanto los PNG
como el SVG. Cuando cada formato tenia su propio codigo de dibujo -y lo tuvo-
la duplicacion no molestaba porque eran cuatro cuadrados; con una silueta, dos
descripciones del mismo dibujo acaban siendo dos dibujos distintos.

Por eso todas las piezas son elipses, incluida la cupula, que es una elipse
cortada por la linea del suelo: es lo unico que los dos formatos saben pintar
identico sin aproximar nada, por distancia al borde en el PNG y con <ellipse>
y un <clipPath> en el SVG. Una curva mas libre obligaria a rasterizar poligonos
aqui y a escribir bezieres alli, que es justo la divergencia que se evita.
"""

import json
import math
import re
import struct
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSS = RAIZ / "assets" / "estilo.css"
ASSETS = RAIZ / "assets"
LISTA = ASSETS / "secciones.json"

# Los dos tonos del monticulo. Estos si viven aqui y no en estilo.css, al reves
# que los de los huevos: no los usa ninguna pagina, son solo del icono. Van en
# ciruela desaturado para que ningun acento de seccion se pierda encima, y no
# mas oscuros porque sobre el fondo (#0f1115) la silueta se emborrona a 32 px.
CUPULA = (0x55, 0x3a, 0x70)
CUPULA_LUZ = (0x86, 0x5f, 0xad)

# A partir de aqui los huevos son mas finos que un pixel en la pestana. No es
# un limite tecnico, es que dejarian de leerse; el dia que llegue hay que
# decidir el dibujo, igual que paso con el 2x2.
MAXIMO_HUEVOS = 8


def acentos():
    """Los sufijos de color de cada seccion, en el orden en que se pintan."""
    secciones = json.loads(LISTA.read_text(encoding="utf-8"))["secciones"]
    nombres = [s["acento"] for s in secciones]
    if not 1 <= len(nombres) <= MAXIMO_HUEVOS:
        raise SystemExit(
            f"ERROR: el icono lleva un huevo por seccion y {LISTA.name} tiene "
            f"{len(nombres)}.\n"
            f"Por encima de {MAXIMO_HUEVOS} cada huevo no llega a un pixel en "
            "la pestana, asi que hay que decidir antes que dibujo se quiere "
            "en vez de pintar manchas que no se distinguen."
        )
    return nombres


def color(css, nombre):
    """El valor de una variable CSS, en la primera vez que aparece.

    La primera es la del :root oscuro; mas abajo el bloque de tema claro
    redefine alguna, y el icono se mira sobre el fondo del sistema, no sobre
    el de la pagina.
    """
    encontrado = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % nombre, css)
    if not encontrado:
        raise SystemExit(
            f"ERROR: no encuentro la variable --{nombre} en {CSS}.\n"
            "Los colores del icono se leen del CSS para que no se "
            "desincronicen. Si la has renombrado, cambia tambien este script."
        )
    crudo = encontrado.group(1)
    return tuple(int(crudo[i:i + 2], 16) for i in (1, 3, 5))


def elipse(cx, cy, rx, ry, tinta, suelo=None):
    return {"cx": cx, "cy": cy, "rx": rx, "ry": ry, "tinta": tinta,
            "suelo": suelo}


def formas(lado, colores, fondo, margen):
    """El dibujo entero, en orden de pintado. La unica fuente: de aqui salen
    los PNG y el SVG.

    Las medidas van en fracciones de la zona util para que el mismo dibujo
    valga a 32 y a 512 px, y para que el margen extra del icono maskable no
    obligue a recolocar nada.
    """
    util = lado * (1 - 2 * margen)
    cx = lado / 2
    suelo = lado * margen + util * 0.75

    piezas = []

    # Los dos hombros, que son lo que hace que esto sea un monticulo. Con una
    # sola elipse cortada por el suelo la silueta sale como un arco de circo
    # perfecto, que se lee antes como un arcoiris que como algo vivo.
    for costado in (-1, 1):
        piezas.append(elipse(cx + costado * util * 0.26, suelo - util * 0.02,
                             util * 0.24, util * 0.33, CUPULA, suelo))

    piezas += [
        # El cuerpo, mas alto y estrecho que los hombros. Todas van cortadas
        # por la linea del suelo: es el corte lo que les da base plana.
        elipse(cx, suelo - util * 0.11, util * 0.37, util * 0.52, CUPULA,
               suelo),
        # El domo interior, que es todo el volumen que hace falta: dos tonos
        # planos se leen a 32 px y un degradado no.
        elipse(cx, suelo - util * 0.065, util * 0.26, util * 0.42, CUPULA_LUZ,
               suelo),
        # La abertura, ancha y en el tercio alto. Estrecha se lee a 32 px como
        # un mordisco en el contorno y no como un agujero, que es la diferencia
        # entre un monticulo y un criadero; probadas las dos, gana esta.
        # Del color del fondo y no de un tono mas oscuro, para que siga siendo
        # un agujero en el icono de Apple y en el maskable, que van opacos.
        elipse(cx, suelo - util * 0.40, util * 0.175, util * 0.078, fondo),
    ]

    # Un huevo por seccion, repartido en dos filas: los pares delante y los
    # impares asomando entre ellos. Repartir en vez de alinearlos deja los
    # huevos al doble de tamano, que a 32 px es la diferencia entre una mancha
    # de color y nada.
    paso = util * 0.28
    rx, ry = util * 0.092, util * 0.114
    filas = (
        (colores[1::2], 0.82, suelo - util * 0.11),
        (colores[0::2], 1.00, suelo - util * 0.02),
    )
    for tintas, escala, cy in filas:
        for i, tinta in enumerate(tintas):
            x = cx + (i - (len(tintas) - 1) / 2) * paso
            piezas.append(elipse(x, cy, rx * escala, ry * escala, tinta))
    return piezas


def cobertura(px, py, pieza):
    """Cuanto cubre una elipse a este pixel, de 0 a 1.

    Distancia con signo al borde: por encima de medio pixel esta dentro del
    todo, por debajo fuera, y en medio se suaviza. Sale mas barato que dibujar
    el icono a triple tamano y reducirlo, y el borde queda igual de limpio.
    """
    dx = (px - pieza["cx"]) / pieza["rx"]
    dy = (py - pieza["cy"]) / pieza["ry"]
    # La distancia real a una elipse no tiene formula cerrada; esta es exacta
    # en un circulo y sobra para las de aqui, que son todas casi redondas. Solo
    # se usa para el medio pixel del borde.
    fuera = (math.hypot(dx, dy) - 1) * min(pieza["rx"], pieza["ry"])
    cubre = min(max(0.5 - fuera, 0), 1)
    if pieza["suelo"] is not None:
        cubre = min(cubre, max(0.5 + (pieza["suelo"] - py), 0), 1)
    return cubre


def dentro(px, py, cx, cy, lado, radio):
    """Lo mismo para el cuadrado redondeado del fondo."""
    dx = max(abs(px - cx) - (lado / 2 - radio), 0)
    dy = max(abs(py - cy) - (lado / 2 - radio), 0)
    return min(max(0.5 - (math.hypot(dx, dy) - radio), 0), 1)


def mezclar(fondo, encima, cubre):
    return tuple(round(f + (e - f) * cubre) for f, e in zip(fondo, encima))


def dibujar(lado, colores, fondo, margen, radio_fondo, con_fondo=True):
    """Devuelve las filas del icono en RGBA."""
    piezas = formas(lado, colores, fondo, margen)
    # El marco de cada pieza, para no calcular una distancia por pixel y pieza:
    # a 512 px son dos millones y medio de cuentas que casi siempre dan cero.
    marcos = [(p["cx"] - p["rx"] - 1, p["cx"] + p["rx"] + 1,
               p["cy"] - p["ry"] - 1, p["cy"] + p["ry"] + 1) for p in piezas]
    centro = lado / 2

    filas = []
    for y in range(lado):
        fila = bytearray()
        py = y + 0.5
        visibles = [(p, m) for p, m in zip(piezas, marcos)
                    if m[2] <= py <= m[3]]
        for x in range(lado):
            px = x + 0.5

            if con_fondo:
                alfa = dentro(px, py, centro, centro, lado, radio_fondo)
            else:
                alfa = 1.0
            pixel = fondo

            for pieza, marco in visibles:
                if not marco[0] <= px <= marco[1]:
                    continue
                cubre = cobertura(px, py, pieza)
                if cubre:
                    pixel = mezclar(pixel, pieza["tinta"], cubre)
                    alfa = max(alfa, cubre)

            fila += bytes(pixel) + bytes([round(alfa * 255)])
        filas.append(bytes(fila))
    return filas


def escribir_png(ruta, ancho, alto, filas):
    def trozo(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos +
                struct.pack(">I", zlib.crc32(tipo + datos) & 0xffffffff))

    crudo = b"".join(b"\x00" + fila for fila in filas)
    png = (b"\x89PNG\r\n\x1a\n" +
           trozo(b"IHDR", struct.pack(">2I5B", ancho, alto, 8, 6, 0, 0, 0)) +
           trozo(b"IDAT", zlib.compress(crudo, 9)) +
           trozo(b"IEND", b""))
    ruta.write_bytes(png)
    print(f"  {ruta.relative_to(RAIZ)}  ({len(png) // 1024 or 1} KB)")


def svg(colores, fondo):
    """El favicon, en vectorial: a 16 px un PNG se ve sucio y este no."""
    lado, margen = 512, 0.14
    piezas = formas(lado, colores, fondo, margen)
    # Las dos piezas recortadas comparten la misma linea de suelo, asi que
    # basta un clip para las dos.
    suelo = next(p["suelo"] for p in piezas if p["suelo"] is not None)

    salida = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">'
        % (lado, lado),
        '  <defs><clipPath id="suelo">'
        '<rect x="0" y="0" width="%d" height="%.1f"/></clipPath></defs>'
        % (lado, suelo),
        '  <rect width="%d" height="%d" rx="114" fill="#%02x%02x%02x"/>'
        % (lado, lado, *fondo),
    ]
    for p in piezas:
        recorte = ' clip-path="url(#suelo)"' if p["suelo"] is not None else ""
        salida.append(
            '  <ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" '
            'fill="#%02x%02x%02x"%s/>'
            % (p["cx"], p["cy"], p["rx"], p["ry"], *p["tinta"], recorte))
    salida.append("</svg>")
    return "\n".join(salida) + "\n"


def compartir(ancho, alto, colores, fondo):
    """La imagen que sale al pegar el enlace en WhatsApp: el icono, centrado.

    Sin texto: dibujar letras a mano con rectangulos queda peor que no
    ponerlas, y el titulo y la descripcion ya salen al lado como texto.
    """
    # Sin fondo redondeado propio: aqui el fondo ya lo pone el lienzo, y un
    # cuadrado redondeado encima deja sus cuatro esquinas transparentes, que
    # es lo que salia como manchas blancas al componerlo.
    marca = 340
    filas_marca = dibujar(marca, colores, fondo, 0.02, 0, con_fondo=False)
    izquierda = (ancho - marca) // 2
    arriba = (alto - marca) // 2

    vacia = bytes(fondo) + b"\xff"
    filas = []
    for y in range(alto):
        if arriba <= y < arriba + marca:
            fila = filas_marca[y - arriba]
            filas.append(vacia * izquierda + fila +
                         vacia * (ancho - izquierda - marca))
        else:
            filas.append(vacia * ancho)
    return filas


def main():
    css = CSS.read_text(encoding="utf-8")
    secciones = acentos()
    colores = [color(css, "acento-" + s) for s in secciones]
    fondo = color(css, "fondo")

    print("Colores leidos de assets/estilo.css:")
    for nombre, tinta in zip(secciones, colores):
        print("  --acento-%-4s #%02x%02x%02x" % (nombre, *tinta))
    print("  --fondo    #%02x%02x%02x" % fondo)
    print()

    (ASSETS / "icono.svg").write_text(svg(colores, fondo), encoding="utf-8")
    print("  assets/icono.svg")

    # Los dos del manifest y el de Apple: fondo redondeado, como se ve en la
    # pantalla de inicio.
    for lado in (192, 512):
        escribir_png(ASSETS / f"icono-{lado}.png", lado, lado,
                     dibujar(lado, colores, fondo, 0.14, lado * 0.22))

    # iOS redondea el icono el solo y no lleva bien la transparencia, asi que
    # este va cuadrado y opaco.
    escribir_png(ASSETS / "icono-180.png", 180, 180,
                 dibujar(180, colores, fondo, 0.17, 0, con_fondo=False))

    # Android recorta los "maskable" a un circulo y solo garantiza el 80%
    # central: el dibujo va mas pequeno para que no le corte una esquina.
    escribir_png(ASSETS / "icono-maskable-512.png", 512, 512,
                 dibujar(512, colores, fondo, 0.26, 0, con_fondo=False))

    escribir_png(ASSETS / "og.png", 1200, 630,
                 compartir(1200, 630, colores, fondo))


if __name__ == "__main__":
    main()
