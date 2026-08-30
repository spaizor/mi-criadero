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

formas() dibuja en sus propias coordenadas y encajar() lo lleva al lienzo, en
vez de escribir las medidas como fracciones del lado. Asi el dibujo llena
siempre el cuadro: al quitarle el fondo se noto que sobraba un cuarto del alto,
y sobre todo el ancho depende de cuantas secciones haya, que es lo que ninguna
medida fija podia saber.
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

# Los tonos del monticulo. Estos si viven aqui y no en estilo.css, al reves que
# los de los huevos: no los usa ninguna pagina, son solo del icono. Van en
# ciruela desaturado para que ningun acento de seccion se pierda encima, y no
# mas oscuros porque sobre un fondo oscuro la silueta se emborrona a 32 px.
CUPULA = (0x55, 0x3a, 0x70)
CUPULA_LUZ = (0x86, 0x5f, 0xad)
# La abertura ya no puede ser del color del fondo, porque los iconos que mas se
# ven ya no tienen fondo: sobre una pestana en tema claro esa elipse se veria
# como una mancha oscura fuera de sitio. Es un ciruela casi negro, que se lee
# como un agujero contra el blanco y contra el negro, y que ademas sigue
# valiendo en los dos iconos que si van opacos.
BOCA = (0x2a, 0x1b, 0x3a)

# A partir de aqui los huevos son mas finos que un pixel en la pestana. No es
# un limite tecnico, es que dejarian de leerse; el dia que llegue hay que
# decidir el dibujo, igual que paso con el 2x2.
MAXIMO_HUEVOS = 8

# El aire alrededor del dibujo en los iconos sin fondo. Es pequeno a proposito:
# sin la pastilla oscura detras, el margen no separa de nada, solo encoge.
MARGEN = 0.04


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


def formas(colores):
    """El dibujo entero, en orden de pintado y en coordenadas propias.

    La unica fuente: de aqui salen los PNG y el SVG. Las medidas son sobre 100
    y no sobre el lado del icono porque quien las lleva al lienzo es encajar().
    """
    suelo = 75.0
    cx = 50.0

    piezas = []

    # Los dos hombros, que son lo que hace que esto sea un monticulo. Con una
    # sola elipse cortada por el suelo la silueta sale como un arco de circo
    # perfecto, que se lee antes como un arcoiris que como algo vivo.
    for costado in (-1, 1):
        piezas.append(elipse(cx + costado * 24.0, suelo - 2.0, 22.0, 37.0,
                             CUPULA, suelo))

    piezas += [
        # El cuerpo, mas alto y estrecho que los hombros. Todas van cortadas
        # por la linea del suelo: es el corte lo que les da base plana.
        elipse(cx, suelo - 11.0, 37.0, 52.0, CUPULA, suelo),
        # El domo interior, que es todo el volumen que hace falta: dos tonos
        # planos se leen a 32 px y un degradado no.
        elipse(cx, suelo - 6.5, 26.0, 46.0, CUPULA_LUZ, suelo),
        # La abertura, ancha, achatada y con aro de cupula por encima. Las tres
        # cosas se decidieron mirandola a 16, 24, 32 y 48 px: estrecha se lee
        # como un mordisco en el contorno y no como un agujero, y pegada al
        # borde de arriba deja una franja fina que convierte el conjunto en el
        # asa de un bolso.
        elipse(cx, suelo - 37.0, 14.5, 6.5, BOCA),
    ]

    # Un huevo por seccion, repartido en dos filas: los pares delante y los
    # impares asomando entre ellos. Repartir en vez de alinearlos deja los
    # huevos al doble de tamano, que a 32 px es la diferencia entre una mancha
    # de color y nada.
    paso, rx, ry = 26.0, 8.8, 10.5
    filas = (
        (colores[1::2], 0.82, suelo - 12.0),
        (colores[0::2], 1.00, suelo - 3.5),
    )
    for tintas, escala, cy in filas:
        for i, tinta in enumerate(tintas):
            x = cx + (i - (len(tintas) - 1) / 2) * paso
            piezas.append(elipse(x, cy, rx * escala, ry * escala, tinta))
    return piezas


def encajar(piezas, lado, margen):
    """Escala y centra el dibujo para que llene el lienzo.

    El alto se mide con el suelo puesto: las elipses cortadas no llegan hasta
    donde llegaria su radio, y sin tenerlo en cuenta el dibujo saldria pequeno
    y subido.
    """
    izq = min(p["cx"] - p["rx"] for p in piezas)
    der = max(p["cx"] + p["rx"] for p in piezas)
    alto = min(p["cy"] - p["ry"] for p in piezas)
    bajo = max(min(p["cy"] + p["ry"], p["suelo"]) if p["suelo"] is not None
               else p["cy"] + p["ry"] for p in piezas)

    escala = lado * (1 - 2 * margen) / max(der - izq, bajo - alto)
    dx = (lado - (der - izq) * escala) / 2 - izq * escala
    dy = (lado - (bajo - alto) * escala) / 2 - alto * escala
    return [elipse(p["cx"] * escala + dx, p["cy"] * escala + dy,
                   p["rx"] * escala, p["ry"] * escala, p["tinta"],
                   None if p["suelo"] is None
                   else p["suelo"] * escala + dy)
            for p in piezas]


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


def mezclar(debajo, encima, cubre):
    return tuple(round(f + (e - f) * cubre) for f, e in zip(debajo, encima))


def dibujar(lado, colores, margen=MARGEN, fondo=None):
    """Devuelve las filas del icono en RGBA. Sin fondo, el icono es la silueta
    recortada y lo de detras es transparente."""
    piezas = encajar(formas(colores), lado, margen)
    # El marco de cada pieza, para no calcular una distancia por pixel y pieza:
    # a 512 px son cinco millones de cuentas que casi siempre dan cero.
    marcos = [(p["cx"] - p["rx"] - 1, p["cx"] + p["rx"] + 1,
               p["cy"] - p["ry"] - 1, p["cy"] + p["ry"] + 1) for p in piezas]
    # Lo de debajo de la silueta cuando no hay fondo. El color da igual mientras
    # el alfa sea cero, pero no puede ser negro: al mezclarse en el medio pixel
    # del borde dejaria un halo sucio alrededor de todo el dibujo.
    vacio = fondo or CUPULA

    filas = []
    for y in range(lado):
        fila = bytearray()
        py = y + 0.5
        visibles = [(p, m) for p, m in zip(piezas, marcos)
                    if m[2] <= py <= m[3]]
        for x in range(lado):
            px = x + 0.5
            pixel, alfa = vacio, 1.0 if fondo else 0.0

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


def svg(colores, margen=MARGEN):
    """El favicon, en vectorial: a 16 px un PNG se ve sucio y este no."""
    lado = 512
    piezas = encajar(formas(colores), lado, margen)
    # Las tres piezas recortadas comparten la misma linea de suelo, asi que
    # basta un clip para las tres.
    suelo = next(p["suelo"] for p in piezas if p["suelo"] is not None)

    salida = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">'
        % (lado, lado),
        '  <defs><clipPath id="suelo">'
        '<rect x="0" y="0" width="%d" height="%.1f"/></clipPath></defs>'
        % (lado, suelo),
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
    # Esta va opaca: una previsualizacion con transparencia se compone contra
    # lo que decida cada aplicacion, y ahi el fondo de la web es la respuesta
    # buena. Como el dibujo ya no lleva pastilla redondeada, se pega sin mas.
    marca = 460
    filas_marca = dibujar(marca, colores, 0.02, fondo)
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

    # El favicon y los dos del manifest van sin fondo: el icono es la silueta,
    # no una pastilla oscura, que en una pestana o un escritorio claros se ve
    # como un parche pegado.
    (ASSETS / "icono.svg").write_text(svg(colores), encoding="utf-8")
    print("  assets/icono.svg")

    for lado in (192, 512):
        escribir_png(ASSETS / f"icono-{lado}.png", lado, lado,
                     dibujar(lado, colores))

    # iOS redondea el icono el solo y no lleva bien la transparencia: se la
    # rellena de negro. Asi que este va cuadrado y opaco, y con algo mas de
    # margen porque el redondeo se come las esquinas.
    escribir_png(ASSETS / "icono-180.png", 180, 180,
                 dibujar(180, colores, 0.10, fondo))

    # El maskable tambien va opaco de borde a borde, y por lo mismo: Android le
    # aplica su propia forma y una esquina transparente se veria recortada.
    # Ademas solo garantiza el 80% central, asi que el dibujo va mas pequeno
    # para que el recorte circular no le corte los hombros.
    escribir_png(ASSETS / "icono-maskable-512.png", 512, 512,
                 dibujar(512, colores, 0.20, fondo))

    escribir_png(ASSETS / "og.png", 1200, 630,
                 compartir(1200, 630, colores, fondo))


if __name__ == "__main__":
    main()
