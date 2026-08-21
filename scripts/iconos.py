#!/usr/bin/env python3
"""Genera el icono de la web en sus cinco tamanos, y la imagen de compartir.

Existe para que el icono no sea un binario opaco: los colores salen de
assets/estilo.css, asi que el dia que cambie el acento de una seccion se
regenera con `python3 scripts/iconos.py` en vez de repintarlo a mano.

El dibujo son los cuatro colores de seccion en rejilla, en el mismo orden que
la portada. Sin letras a proposito: a 32 px una inicial no se lee, y cuatro
manchas de color si se reconocen de un vistazo entre veinte pestanas.

Solo biblioteca estandar, como el resto de scripts del proyecto: el PNG se
escribe a mano (zlib + struct), que para figuras planas son treinta lineas.
"""

import math
import re
import struct
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSS = RAIZ / "assets" / "estilo.css"
ASSETS = RAIZ / "assets"

# Orden de la portada: tecnologia, IA, nintendo, ofertas.
SECCIONES = ("tec", "ia", "nin", "ofe")


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


def dentro(px, py, cx, cy, lado, radio):
    """Cuanto cubre un cuadrado redondeado a este pixel, de 0 a 1.

    Distancia con signo al borde: por encima de medio pixel esta dentro del
    todo, por debajo fuera, y en medio se suaviza. Sale mas barato que dibujar
    el icono a triple tamano y reducirlo, y el borde queda igual de limpio.
    """
    dx = max(abs(px - cx) - (lado / 2 - radio), 0)
    dy = max(abs(py - cy) - (lado / 2 - radio), 0)
    return min(max(0.5 - (math.hypot(dx, dy) - radio), 0), 1)


def mezclar(fondo, encima, cobertura):
    return tuple(round(f + (e - f) * cobertura) for f, e in zip(fondo, encima))


def dibujar(lado, colores, fondo, margen, radio_fondo, con_fondo=True):
    """Devuelve las filas del icono en RGBA."""
    # Zona util y tamano de cada cuadro: dos cuadros y un hueco entre ellos.
    util = lado * (1 - 2 * margen)
    hueco = util * 0.09
    cuadro = (util - hueco) / 2
    radio = cuadro * 0.22
    centro = lado / 2

    # Centro de cada uno de los cuatro, en el orden de la portada.
    centros = [
        (centro - (cuadro + hueco) / 2, centro - (cuadro + hueco) / 2),
        (centro + (cuadro + hueco) / 2, centro - (cuadro + hueco) / 2),
        (centro - (cuadro + hueco) / 2, centro + (cuadro + hueco) / 2),
        (centro + (cuadro + hueco) / 2, centro + (cuadro + hueco) / 2),
    ]

    filas = []
    for y in range(lado):
        fila = bytearray()
        py = y + 0.5
        for x in range(lado):
            px = x + 0.5

            if con_fondo:
                cobertura = dentro(px, py, centro, centro, lado, radio_fondo)
                pixel, alfa = fondo, cobertura
            else:
                pixel, alfa = fondo, 1.0

            for (cx, cy), tinta in zip(centros, colores):
                cubre = dentro(px, py, cx, cy, cuadro, radio)
                if cubre:
                    pixel = mezclar(pixel, tinta, cubre)
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
    util = lado * (1 - 2 * margen)
    hueco = util * 0.09
    cuadro = (util - hueco) / 2
    radio = cuadro * 0.22
    inicio = lado * margen

    posiciones = [
        (inicio, inicio),
        (inicio + cuadro + hueco, inicio),
        (inicio, inicio + cuadro + hueco),
        (inicio + cuadro + hueco, inicio + cuadro + hueco),
    ]

    piezas = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">',
        '  <rect width="512" height="512" rx="114" fill="#%02x%02x%02x"/>' % fondo,
    ]
    for (x, y), tinta in zip(posiciones, colores):
        piezas.append(
            '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" '
            'fill="#%02x%02x%02x"/>' % (x, y, cuadro, cuadro, radio, *tinta))
    piezas.append('</svg>')
    return "\n".join(piezas) + "\n"


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
            filas.append(vacia * izquierda + fila + vacia * (ancho - izquierda - marca))
        else:
            filas.append(vacia * ancho)
    return filas


def main():
    css = CSS.read_text(encoding="utf-8")
    colores = [color(css, "acento-" + s) for s in SECCIONES]
    fondo = color(css, "fondo")

    print("Colores leidos de assets/estilo.css:")
    for nombre, tinta in zip(SECCIONES, colores):
        print("  --acento-%-4s #%02x%02x%02x" % (nombre, *tinta))
    print("  --fondo    #%02x%02x%02x" % fondo)
    print()

    (ASSETS / "icono.svg").write_text(svg(colores, fondo), encoding="utf-8")
    print(f"  assets/icono.svg")

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
