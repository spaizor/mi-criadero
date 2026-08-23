#!/usr/bin/env python3
"""Trabajo mecanico de las rutinas de noticias.

Todo lo que no requiere criterio vive aqui y no en el prompt: una instruccion
del prompt se paga en cada ejecucion, y ademas puede olvidarse. Un script no.

    python3 scripts/noticias.py candidatos <seccion> [--horas N] [--por-medio N]
    python3 scripts/noticias.py titulares  <seccion> [--maximo N] [--probar]
    python3 scripts/noticias.py anteriores <seccion> [--turnos N]
    python3 scripts/noticias.py validar    <seccion>
    python3 scripts/noticias.py archivar   <seccion>
    python3 scripts/noticias.py publicar   "mensaje de commit"
    python3 scripts/noticias.py estado     [--dias N] [--local]

Solo biblioteca estandar: las rutinas corren en un entorno que no controlamos.
"""

import argparse
import gzip
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HISTORICO = RAIZ / "data" / "historico"
MEDIOS = Path(__file__).resolve().parent / "medios.json"

# Las secciones de la web. En assets/ y no en data/ por lo mismo que medios.json:
# 'publicar' hace git add solo de data/, y ahi una rutina podria publicarlo sin
# querer.
SECCIONES = RAIZ / "assets" / "secciones.json"

# Turnos del historico que se miran para detectar noticias ya publicadas.
# 4 son dos dias: repetir algo de anteayer tambien es repetir.
TURNOS_ANTERIORES = 4

FORMATO_FECHA_HORA = "%d-%m-%Y %H:%M"
FORMATO_FECHA = "%d-%m-%Y"

# Limites de reparto. Son los del prompt: si se cambian ahi, cambiarlos aqui.
MAX_DESTACADAS_POR_MEDIO = 2
MAX_TITULARES_POR_MEDIO = 5
MAX_TITULARES = 25

# Minimos por turno. El turno de tarde solo puede coger lo publicado desde la
# manana, asi que exigirle lo mismo solo consigue que se rellene con paja.
MIN_TITULARES = {"M": 15, "T": 8}
MIN_MEDIOS_TITULARES = {"M": 5, "T": 3}

# Y los de las secciones que no dan para tanto. Una seccion estrecha no es una
# seccion mal hecha: 'ia' se midio antes de abrirla y da 18 candidatos por turno
# contra los 50 de tecnologia, asi que pedirle 25 titulares solo conseguiria que
# 'validar' avisara en todas las ejecuciones y se dejara de leer. Los avisos
# valen para algo mientras signifiquen que ha pasado algo raro.
CUPOS = {
    "ia": {
        "max_titulares": 15,
        "min_titulares": {"M": 8, "T": 5},
        "min_medios": {"M": 4, "T": 3},
        # En tecnologia exigir una destacada espanola es razonable: sus medios
        # espanoles dan 25 candidatos por turno. Aqui dan 2, asi que habra
        # turnos sin ninguna noticia espanola de IA, y eso no es un fallo de la
        # ejecucion ni algo que pueda arreglar. Un ERROR que quien lo recibe no
        # puede corregir solo ensena a saltarse los errores.
        "destacada_espanola": "aviso",
    },
}


def cupo(seccion, cual, por_defecto):
    return CUPOS.get(seccion, {}).get(cual, por_defecto)

# Horas hacia atras que mira 'candidatos' cuando no hay turno anterior.
HORAS_POR_DEFECTO = 18

# Hora a partir de la cual 'estado' da por perdido un turno que no esta. Las
# rutinas salen a las 4:00 y las 16:30 (una hora menos en invierno), asi que
# esto es margen de sobra: antes de su limite un turno que falta esta pendiente,
# no perdido, y avisar de el seria una falsa alarma cada manana.
LIMITE_TURNO = {"M": 9, "T": 21}

AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Titulares que no son noticia: guias, ofertas, listas y analisis. Se descartan
# antes de ensenarlos para que no acaben de relleno un dia flojo.
#
# El segundo bloque salio de medir las 1.211 noticias publicadas entre el
# 08-08-2026 y el 21-08-2026: son las formulas exactas que se colaron, no
# terminos imaginados. Cada una se probo contra ese historico y ninguna toca
# una noticia de verdad, que es el criterio de esta lista: aqui el peligro es
# colar de mas, no quedarse corto.
#
# Dos cosas que parecian obvias y se cayeron al medirlas:
# - "rebaja" a secas tira "Digi rebaja el roaming en cuatro paises", que es
#   noticia de telecos; y "rebaja el precio" no aparecio ni una vez.
# - "por menos de N" tira "Xiaomi lanza una lavadora un 30% mas eficiente por
#   menos de 450 euros", que es un lanzamiento. "por solo N" no falla.
RUIDO = re.compile(
    r"^(como |cómo |guia|guía|analisis|análisis|review|top \d|los mejores|"
    r"las mejores|mejores |ofertas|chollo|ver online|donde ver|dónde ver)"
    r"|oferta|descuento|rebajad|precio m[ií]nimo|cupon|cupón"
    # Formulas de compra que se colaban por no ir al principio del titular.
    r"|,\s*(analisis|análisis|review)\s*:"
    r"|(desploma|hunde|tumba|derrumba)[^.]{0,20}precio"
    r"|ah[óo]rrate|cons[íi]guelo|hazte con [ée]l|por s[óo]?lo \d"
    # En primera persona es el medio quien regala: publirreportaje, no noticia.
    r"|sorteo|sorteamos|regalamos|patrocinad",
    re.IGNORECASE,
)


def ruta_actual(seccion):
    return RAIZ / "data" / f"{seccion}.json"


def carpeta_historico(seccion):
    return HISTORICO / seccion


def leer_json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def partir_actualizado(actualizado):
    """'08-08-2026 06:15' -> ('2026-08-08', 'M', datetime)"""
    momento = datetime.strptime(actualizado, FORMATO_FECHA_HORA)
    turno = "M" if momento.hour < 12 else "T"
    return momento.strftime("%Y-%m-%d"), turno, momento


def leer_indice(seccion):
    ruta = carpeta_historico(seccion) / "indice.json"
    if not ruta.exists():
        return {"seccion": seccion, "entradas": []}
    return leer_json(ruta)


def zona_espanola():
    """Europe/Madrid, o el desfase de verano/invierno si no hay tzdata."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Madrid")
    except Exception:
        mes = datetime.now().month
        return timezone(timedelta(hours=2 if 4 <= mes <= 10 else 1))


ESPANA = zona_espanola()


def leer_medios(seccion, solo_utiles=True):
    """Medios de la seccion. Utiles = con feed y comprobado; el resto, a mano."""
    if not MEDIOS.exists():
        return []
    secciones = leer_json(MEDIOS).get("secciones", {})
    medios = secciones.get(seccion, {}).get("medios", [])
    if not solo_utiles:
        return medios
    return [m for m in medios if m.get("feed") and m.get("comprobado")]


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def patron_de(terminos):
    """Regex que caza cualquiera de los terminos como palabra suelta."""
    if not terminos:
        return None
    # Sin tildes en los dos lados: un feed que escriba 'Pokemon' tiene que
    # cazar igual que uno que escriba 'Pokemon' con tilde.
    partes = sorted((re.escape(sin_tildes(t)) for t in terminos),
                    key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(partes) + r")(?!\w)", re.IGNORECASE)


def leer_tema(seccion):
    """Terminos que hacen que un titular sea de esta seccion, o None."""
    if not MEDIOS.exists():
        return None
    tema = leer_json(MEDIOS).get("secciones", {}).get(seccion, {}).get("tema")
    return patron_de((tema or {}).get("propio"))


def leer_tema_ajeno(seccion):
    """Terminos que mandan un titular a OTRA seccion, o None.

    Existe porque al abrir 'ia' habia que decidir que pasaba con las noticias de
    IA de tecnologia, que eran el 29% de lo que publicaba. Dejarlas en las dos
    secciones significa que quien entra en Tecnologia y luego en IA se encuentra
    los mismos titulares dos veces: el lector no gana una seccion, pierde media.

    La lista no se copia, se apunta a la de la otra seccion con
    'tema_ajeno': {"de_la_seccion": "ia"}. Dos listas iguales en dos sitios
    empiezan iguales y acaban distintas, y el dia que se desincronizan aparece
    justo el fallo que esto evita: una noticia que ni entra en una ni en otra.
    """
    if not MEDIOS.exists():
        return None
    secciones = leer_json(MEDIOS).get("secciones", {})
    ajeno = secciones.get(seccion, {}).get("tema_ajeno")
    if not ajeno:
        return None
    otra = secciones.get(ajeno.get("de_la_seccion"), {}).get("tema", {})
    return patron_de(otra.get("propio"))


def enlaces_de_la_hermana(seccion, medios):
    """Enlaces que el propio medio ha colgado en su feed de la seccion hermana.

    Es 'de_otra_seccion' llevado a las secciones hermanas: alli la categoria se
    lee en la URL y aqui en de que feed viene la noticia. En los dos casos se
    lee donde la ha puesto el medio en vez de adivinarlo por el titular, que es
    lo que no puede dar falsos positivos.

    Existe porque el filtro por titular ('tema_ajeno') no llega a todo, y se
    vio en las dos primeras ejecuciones con la seccion de IA ya abierta: el
    21-08-2026 y el 22-08-2026 salio una noticia repetida en las dos secciones,
    una por turno. Las dos eran de TechCrunch, que publica la misma entrada en
    su feed general y en el de IA, y ninguna decia en el titular una palabra de
    la lista 'propio': 'Nvidia partners with data center developer Cloverleaf' y
    'Starcloud raises $250 million for orbital data centers'. 'Nvidia' esta
    fuera de esa lista a proposito (vende tarjetas graficas de juego) y 'data
    center' no esta, asi que por titular no habia forma de cazarlas.

    Medido sobre los feeds del 22-08-2026: de las 8 noticias que estaban en los
    dos feeds a la vez, el titular cazaba 6 y se escapaban esas 2.

    Solo mira los medios que publican un feed aparte para la hermana (ahora
    Hipertextual, TechCrunch, The Verge y Ars Technica). Si ese feed no
    responde no se descarta nada suyo y se avisa en el parte: dejar de publicar
    a un medio entero por un fallo de red seria mucho peor que la repetida
    ocasional que esto evita.
    """
    if not MEDIOS.exists():
        return set(), []
    secciones = leer_json(MEDIOS).get("secciones", {})
    ajeno = secciones.get(seccion, {}).get("tema_ajeno")
    if not ajeno:
        return set(), []
    hermana = {m["nombre"].strip().lower(): m
               for m in secciones.get(ajeno.get("de_la_seccion"), {}).get("medios", [])
               if m.get("feed") and m.get("comprobado")}

    enlaces, fallos = set(), []
    for medio in medios:
        otro = hermana.get(medio["nombre"].strip().lower())
        # Que las dos secciones usen el mismo feed no dice nada de la noticia:
        # lo que la clasifica es que el medio tenga un feed aparte para la
        # hermana y la haya puesto ahi.
        if not otro or otro["feed"] == medio.get("feed"):
            continue
        contenido, error = descargar(otro["feed"])
        if contenido is None:
            fallos.append(f"{medio['nombre']}: {error}")
            continue
        try:
            enlaces.update(enlace for _, enlace, _ in entradas_del_feed(contenido))
        except ET.ParseError as e:
            fallos.append(f"{medio['nombre']}: el feed no es XML valido ({e})")
    return enlaces, fallos


def fuera_de_tema(titulo, tema, medio):
    """Titular de un medio generalista que no menciona el tema de la seccion.

    Se exige el tema propio en vez de descartar por plataforma ajena, que era
    lo primero que se probo. Dos motivos, los dos medidos sobre los feeds:

    - Descartar por 'PS5, Xbox, Steam' deja pasar todo lo que no nombra ninguna
      plataforma, que en un medio generalista es medio feed de anime, manga y
      cine. Se colaban 20 de 30 de Areajugones.
    - Y no se pierden los multiplataforma, que es lo que se temia: 'Silksong
      llega a Switch, PS5 y Xbox' nombra Switch, asi que entra igual.

    Solo se aplica a los medios marcados con 'filtrar_tema'. En los de Nintendo
    seria contraproducente: sus noticias dan la consola por sabida y no la
    nombran, asi que exigirsela tiraria la mitad (Nintenderos, 5 de 9).
    """
    if tema is None or not medio.get("filtrar_tema"):
        return False
    return not tema.search(sin_tildes(titulo))


def de_otra_seccion(enlace, medio):
    """Titular que el propio medio ha metido en una categoria que no es la nuestra.

    Se filtra por el enlace, no por el titular, y por eso no puede haber falsos
    positivos: no se adivina de que va la noticia, se lee la seccion en la que
    el medio la ha colgado. Sale de mirar las 1.211 publicadas hasta el
    21-08-2026, donde este era el ruido que quedaba en tecnologia:

    - hipertextual.com/cine-television/ puso 23 titulares, todos de cine y
      series ('Las cinco mejores sitcom de los 2000'). Es el 28% de lo que
      aporta Hipertextual.
    - adslzone.net/ofertas/ puso 8, todos de compra ('AliExpress hunde el
      precio...'). RUIDO no los cazaba porque no dicen 'oferta' ni 'descuento'.

    Ninguno de los 31 era noticia de la seccion, asi que no se pierde nada.
    Solo sirve donde el medio pone la categoria en la URL: en los de Nintendo
    no la ponen (GoNintendo cuelga todo de /contents/) y ahi filtra 'tema'.
    """
    rutas = medio.get("excluir_rutas")
    if not rutas:
        return False
    enlace = enlace.lower()
    return any(ruta.lower() in enlace for ruta in rutas)


def es_de_otra_seccion(titulo, ajeno):
    """Titular que le toca a la seccion hermana. Se aplica a todos los medios.

    Al reves que 'fuera_de_tema', aqui no se distingue entre medios
    especializados y generalistas: lo que decide no es de quien viene la
    noticia sino de que va. Un medio de IA puro no se pone en tecnologia.
    """
    if ajeno is None:
        return False
    return bool(ajeno.search(sin_tildes(titulo)))


def medios_espanoles(seccion):
    # Todos, no solo los que tienen feed: que a un medio le falle el RSS no lo
    # vuelve extranjero, y sus noticias se pueden haber sacado a mano.
    return {m["nombre"].strip().lower()
            for m in leer_medios(seccion, solo_utiles=False)
            if m.get("idioma") == "es"}


def publicados_antes(seccion, turnos=TURNOS_ANTERIORES, excluir=(None, None)):
    """Enlaces ya publicados en los ultimos turnos -> fecha en que salieron."""
    previos = [e for e in leer_indice(seccion).get("entradas", [])
               if (e.get("fecha"), e.get("turno")) != excluir]
    vistos = {}
    for entrada in previos[:turnos]:
        ruta = carpeta_historico(seccion) / entrada["fichero"]
        if not ruta.exists():
            continue
        datos = leer_json(ruta)
        for clave in ("destacadas", "titulares", "noticias"):
            for noticia in datos.get(clave, []):
                if noticia.get("enlace"):
                    vistos.setdefault(noticia["enlace"], entrada["fecha"])
    return vistos


# --------------------------------------------------------------------------
# candidatos: descarga los feeds de medios.json y saca lo publicado desde el
# turno anterior. Es la materia prima de los titulares: titulo, enlace y fecha
# salen del feed, no del criterio de nadie.
# --------------------------------------------------------------------------

def descomprimir(datos, cabeceras):
    """Deshace el gzip o el deflate de una respuesta que venga comprimida.

    Hay servidores que comprimen aunque no se les pida: Vandal manda gzip a
    pelo. Sin esto, lo que llega son bytes binarios que 'entradas_del_feed'
    rechaza como XML invalido, y el medio parecia estar bloqueando a los
    scripts cuando en realidad respondia perfectamente. Se estuvo dando por
    caido por esto, asi que ante la duda se mira tambien el numero magico y no
    solo la cabecera, que no todos la mandan bien.
    """
    codificacion = (cabeceras.get("Content-Encoding") or "").lower()
    if "gzip" in codificacion or datos[:2] == b"\x1f\x8b":
        return gzip.decompress(datos)
    if "deflate" in codificacion:
        try:
            return zlib.decompress(datos)
        except zlib.error:  # deflate crudo, sin la cabecera de zlib
            return zlib.decompress(datos, -zlib.MAX_WBITS)
    return datos


def descargar(url, intentos=3):
    # Varios medios espanoles cortan la conexion al primer intento y responden
    # al segundo, asi que se espera un poco entre intentos en vez de insistir.
    cabeceras = {
        "User-Agent": AGENTE,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    for intento in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=cabeceras)
            with urllib.request.urlopen(peticion, timeout=25) as respuesta:
                return descomprimir(respuesta.read(), respuesta.headers), None
        except Exception as e:  # red, timeout, 404, certificados...
            if intento == intentos:
                return None, str(e)
            time.sleep(2 * intento)
    return None, "sin intentos"


def sin_espacio(tag):
    return tag.rsplit("}", 1)[-1]


def texto_hijo(elemento, nombre):
    for hijo in elemento:
        if sin_espacio(hijo.tag) == nombre and hijo.text:
            return unescape(hijo.text).strip()
    return ""


def enlace_de(elemento):
    """RSS lo pone como texto; Atom, en el atributo href de <link rel=alternate>."""
    directo = texto_hijo(elemento, "link")
    if directo:
        return directo
    for hijo in elemento:
        if sin_espacio(hijo.tag) == "link":
            rel = hijo.attrib.get("rel", "alternate")
            if rel == "alternate" and hijo.attrib.get("href"):
                return hijo.attrib["href"]
    return ""


def fecha_de(elemento):
    for nombre in ("pubDate", "published", "updated", "date"):
        valor = texto_hijo(elemento, nombre)
        if not valor:
            continue
        try:
            momento = parsedate_to_datetime(valor)
        except (TypeError, ValueError):
            try:
                momento = datetime.fromisoformat(valor.replace("Z", "+00:00"))
            except ValueError:
                continue
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
        return momento.astimezone(ESPANA)
    return None


def entradas_del_feed(contenido):
    raiz = ET.fromstring(contenido)
    piezas = [e for e in raiz.iter() if sin_espacio(e.tag) in ("item", "entry")]
    salida = []
    for pieza in piezas:
        titulo = texto_hijo(pieza, "title")
        enlace = enlace_de(pieza)
        if titulo and enlace:
            salida.append((titulo, enlace, fecha_de(pieza)))
    return salida


def ventana_del_turno(seccion, horas=0):
    """Desde cuando se cogen noticias, y como explicarselo a quien mire."""
    ahora = datetime.now(ESPANA)
    if horas:
        return ahora - timedelta(hours=horas), f"ultimas {horas} h"
    entradas = leer_indice(seccion).get("entradas", [])
    previo = (validar_fecha(entradas[0]["actualizado"], FORMATO_FECHA_HORA)
              if entradas else None)
    if previo:
        return (previo.replace(tzinfo=ESPANA),
                f"turno anterior ({entradas[0]['actualizado']})")
    return (ahora - timedelta(hours=HORAS_POR_DEFECTO),
            f"ultimas {HORAS_POR_DEFECTO} h (no hay turno anterior)")


def cmd_candidatos(args):
    medios = leer_medios(args.seccion)
    if not medios:
        print(f"ERROR: no hay medios comprobados para '{args.seccion}' en "
              f"scripts/medios.json. Repasa ese fichero.")
        return 1

    corte, desde = ventana_del_turno(args.seccion, args.horas)
    ya_publicado = publicados_antes(args.seccion)
    tema = leer_tema(args.seccion)
    ajeno = leer_tema_ajeno(args.seccion)
    de_la_hermana, fallos_hermana = enlaces_de_la_hermana(args.seccion, medios)

    candidatos, fallos, descartes, vistos = [], [], Counter(), set()
    for medio in medios:
        contenido, error = descargar(medio["feed"])
        if contenido is None:
            fallos.append(f"{medio['nombre']}: {error}")
            continue
        try:
            entradas = entradas_del_feed(contenido)
        except ET.ParseError as e:
            fallos.append(f"{medio['nombre']}: el feed no es XML valido ({e})")
            continue

        del_medio, repetidos = [], set()
        for titulo, enlace, fecha in entradas:
            if fecha is None or fecha < corte:
                descartes["viejas o sin fecha"] += 1
                continue
            # Hay feeds que traen la misma noticia dos veces (HobbyConsolas lo
            # hace), asi que no basta con mirar lo ya publicado.
            clave = sin_tildes(titulo).strip().lower()
            if enlace in ya_publicado or enlace in vistos or clave in repetidos:
                descartes["ya publicadas o repetidas"] += 1
                continue
            vistos.add(enlace)
            repetidos.add(clave)
            if RUIDO.search(titulo):
                descartes["guias, ofertas y analisis"] += 1
                continue
            if de_otra_seccion(enlace, medio):
                descartes["de otra seccion del propio medio"] += 1
                continue
            if fuera_de_tema(titulo, tema, medio):
                descartes["de otra plataforma"] += 1
                continue
            if es_de_otra_seccion(titulo, ajeno):
                descartes["le tocan a la seccion hermana"] += 1
                continue
            if enlace in de_la_hermana:
                descartes["colgadas por el medio en su feed de la hermana"] += 1
                continue
            del_medio.append({
                "titulo_original": titulo,
                "fuente": medio["nombre"],
                "enlace": enlace,
                "fecha": fecha.strftime(FORMATO_FECHA),
                "publicado": fecha.strftime(FORMATO_FECHA_HORA),
            })
        del_medio.sort(key=lambda c: c["publicado"], reverse=True)
        candidatos.extend(del_medio[: args.por_medio])

    candidatos.sort(key=lambda c: c["publicado"], reverse=True)

    print(f"# {len(candidatos)} candidatos de {len(medios) - len(fallos)} medios, "
          f"desde el {desde}.")
    print("# 'titulo_original' viene del feed TAL CUAL: hay que reescribirlo en "
          "espanol antes de publicarlo.")
    print("# La fecha sale del propio feed, no se toca.")
    print(f"# Los titulares de los medios espanoles los pone solo 'titulares "
          f"{args.seccion}'. De esta lista salen las destacadas y los titulares "
          f"de los medios de fuera, que si hay que traducir.")
    for motivo, veces in descartes.most_common():
        print(f"# Descartadas {veces} por {motivo}.")
    for fallo in fallos:
        print(f"# FEED CAIDO {fallo}")
    for fallo in fallos_hermana:
        print(f"# FEED HERMANO CAIDO {fallo}: no se ha podido comprobar si sus "
              f"noticias le tocan a la otra seccion, asi que puede colarse "
              f"alguna repetida.")
    utiles = {m["nombre"] for m in medios}
    for medio in leer_medios(args.seccion, solo_utiles=False):
        if medio["nombre"] not in utiles:
            print(f"# SIN FEED {medio['nombre']} ({medio['web']}): "
                  f"{medio.get('nota') or 'no tiene RSS utilizable'}")
    if len(medios) - len(fallos) < 2:
        print("# Han fallado casi todos los feeds: puede que no haya salida a "
              "internet. Busca los titulares a mano abriendo cada medio.")
    print(json.dumps(candidatos, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------
# titulares: rellena el bloque de titulares con los medios espanoles, sin que
# pase por el modelo. En un medio espanol no hay nada que traducir: el titulo
# del feed ya es publicable, y copiarlo es justo donde se inventaban las horas
# y las fuentes. El modelo se queda con las destacadas y los medios de fuera.
# --------------------------------------------------------------------------

def limpiar_titulo(titulo):
    """El titulo del feed tal cual, pero sin restos del XML."""
    # unescape otra vez porque hay feeds que escapan dos veces (&amp;amp;), y
    # sin saltos de linea ni espacios dobles, que en el JSON cantan mucho.
    return " ".join(unescape(titulo).split())


def turno_ya_archivado(seccion, datos):
    """True si el JSON que hay en data/ es un turno ya archivado.

    Protege del caso feo: el modelo no ha llegado a escribir su fichero y en
    data/<seccion>.json sigue el del turno pasado. Sin esto, 'titulares' le
    anadiria las noticias de hoy al turno de ayer y lo publicaria como suyo.
    """
    try:
        fecha, turno, _ = partir_actualizado(str(datos.get("actualizado", "")))
    except ValueError:
        return False
    return any(e.get("fecha") == fecha and e.get("turno") == turno
               for e in leer_indice(seccion).get("entradas", []))


def cmd_titulares(args):
    if args.maximo is None:
        args.maximo = cupo(args.seccion, "max_titulares", MAX_TITULARES)
    ruta = ruta_actual(args.seccion)
    try:
        datos = leer_json(ruta)
    except FileNotFoundError:
        print(f"ERROR: no existe {ruta.relative_to(RAIZ)}. Este comando rellena "
              f"los titulares de un fichero que ya tiene sus destacadas: "
              f"escribelo primero y lanzalo despues.")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: {ruta.relative_to(RAIZ)} no es JSON valido: {e}")
        return 1

    if turno_ya_archivado(args.seccion, datos):
        print(f"ERROR: data/{args.seccion}.json es del turno "
              f"{datos.get('actualizado')}, que ya esta archivado. Parece el "
              f"fichero del turno anterior: escribe el de este turno (con su "
              f"'actualizado' y sus destacadas) antes de rellenar titulares.")
        return 1

    espanoles = [m for m in leer_medios(args.seccion) if m.get("idioma") == "es"]
    if not espanoles:
        print(f"ERROR: no hay ningun medio espanol comprobado en "
              f"'{args.seccion}' dentro de scripts/medios.json, asi que no hay "
              f"nada que rellenar sin pasar por el modelo.")
        return 1

    destacadas = datos.get("destacadas") or []
    ya_estan = datos.get("titulares") or []
    if not isinstance(destacadas, list) or not isinstance(ya_estan, list):
        print("ERROR: 'destacadas' y 'titulares' tienen que ser listas.")
        return 1

    corte, desde = ventana_del_turno(args.seccion, args.horas)
    tema = leer_tema(args.seccion)
    ajeno = leer_tema_ajeno(args.seccion)
    de_la_hermana, fallos_hermana = enlaces_de_la_hermana(args.seccion, espanoles)
    # Lo de turnos pasados y lo que el modelo ya haya puesto en este.
    vetados = set(publicados_antes(args.seccion))
    vetados.update(n.get("enlace") for n in destacadas + ya_estan if n.get("enlace"))
    # Normalizado: si el modelo escribe 'xataka' y el catalogo 'Xataka', sin
    # esto no se le contarian los que ya ha puesto y se pasaria del maximo.
    hueco = Counter(str(n.get("fuente", "")).strip().lower() for n in ya_estan)

    tope = args.maximo - len(ya_estan)
    if tope <= 0:
        print(f"El fichero ya trae {len(ya_estan)} titulares y el tope es "
              f"{args.maximo}: no cabe ninguno mas. Este comando pone los de "
              f"los medios espanoles, asi que al modelo le tocan solo los de "
              f"fuera; si ha llenado el cupo el, no queda sitio para ellos.")
        return 0

    por_medio, fallos, descartes = {}, [], Counter()
    for medio in espanoles:
        contenido, error = descargar(medio["feed"])
        if contenido is None:
            fallos.append(f"{medio['nombre']}: {error}")
            continue
        try:
            entradas = entradas_del_feed(contenido)
        except ET.ParseError as e:
            fallos.append(f"{medio['nombre']}: el feed no es XML valido ({e})")
            continue

        nuevos, repetidos = [], set()
        for titulo, enlace, fecha in entradas:
            # Hay feeds que traen la misma noticia dos veces (HobbyConsolas lo
            # hace), asi que ademas del enlace se mira el titulo del medio.
            clave = sin_tildes(titulo).strip().lower()
            if fecha is None or fecha < corte:
                descartes["viejas o sin fecha"] += 1
            elif enlace in vetados or clave in repetidos:
                descartes["ya publicadas, ya puestas o repetidas"] += 1
            elif RUIDO.search(titulo):
                descartes["guias, ofertas y analisis"] += 1
            elif de_otra_seccion(enlace, medio):
                descartes["de otra seccion del propio medio"] += 1
            elif fuera_de_tema(titulo, tema, medio):
                descartes["de otra plataforma"] += 1
            elif es_de_otra_seccion(titulo, ajeno):
                descartes["le tocan a la seccion hermana"] += 1
            elif enlace in de_la_hermana:
                descartes["colgadas por el medio en su feed de la hermana"] += 1
            else:
                vetados.add(enlace)
                repetidos.add(clave)
                nuevos.append({
                    "titulo": limpiar_titulo(titulo),
                    "fuente": medio["nombre"],
                    "enlace": enlace,
                    # Sin hora a proposito: no se abre el articulo. La del feed
                    # es la de publicacion, pero el formato de los titulares no
                    # la lleva y anadirla aqui solo la haria parecer verificada.
                    "fecha": fecha.strftime(FORMATO_FECHA),
                    "_publicado": fecha,
                })
        nuevos.sort(key=lambda n: n["_publicado"], reverse=True)
        sitio = MAX_TITULARES_POR_MEDIO - hueco[medio["nombre"].strip().lower()]
        if sitio > 0 and nuevos:
            por_medio[medio["nombre"]] = nuevos[:sitio]

    # Uno de cada medio por vuelta y no los 5 del primero: si un feed largo se
    # lleva todo el hueco, el reparto queda con dos medios y 'validar' avisa.
    elegidos, ronda = [], 0
    while len(elegidos) < tope:
        quedan = [lista for lista in por_medio.values() if len(lista) > ronda]
        if not quedan:
            break
        for lista in quedan:
            if len(elegidos) >= tope:
                break
            elegidos.append(lista[ronda])
        ronda += 1

    print(f"# {len(elegidos)} titulares de {len(espanoles) - len(fallos)} "
          f"medios espanoles, desde el {desde}.")
    print(f"# Titulo, enlace y fecha salen del feed sin tocar: no hay nada que "
          f"traducir ni que resumir en un medio espanol.")
    for motivo, veces in descartes.most_common():
        print(f"# Descartadas {veces} por {motivo}.")
    for fallo in fallos:
        print(f"# FEED CAIDO {fallo}")
    for fallo in fallos_hermana:
        print(f"# FEED HERMANO CAIDO {fallo}: no se ha podido comprobar si sus "
              f"noticias le tocan a la otra seccion, asi que puede colarse "
              f"alguna repetida.")
    for nombre, lista in sorted(por_medio.items()):
        puestos = len([n for n in elegidos if n["fuente"] == nombre])
        if puestos < len(lista):
            print(f"# {nombre}: {puestos} de {len(lista)} (no cabian mas).")

    if not elegidos:
        print("\nNo hay nada nuevo que anadir. Si es la primera ejecucion del "
              "dia, revisa los feeds caidos de arriba antes de darlo por bueno.")
        return 0

    for noticia in elegidos:
        noticia.pop("_publicado")
    # Por dia y estable: dentro del mismo dia se respeta el orden con el que
    # llegaron, que es lo mas parecido a 'lo mas reciente primero' que se puede
    # decir sin hora. Los titulares no la llevan a proposito.
    salida = ya_estan + elegidos
    salida.sort(key=lambda n: validar_fecha(str(n.get("fecha", "")), FORMATO_FECHA)
                or datetime.min, reverse=True)

    if args.probar:
        print("\n--probar: no se ha escrito nada. Se anadirian:")
        for noticia in elegidos:
            print(f"- [{noticia['fuente']}] {noticia['titulo']}")
        return 0

    datos["titulares"] = salida
    escribir_json(ruta, datos)
    print(f"\ndata/{args.seccion}.json: {len(ya_estan)} titulares del modelo + "
          f"{len(elegidos)} de los feeds espanoles = {len(salida)}. Ahora "
          f"'validar {args.seccion}'.")
    return 0


# --------------------------------------------------------------------------
# anteriores: que se publico en los ultimos turnos, para no repetirlo
# --------------------------------------------------------------------------

def cmd_anteriores(args):
    entradas = leer_indice(args.seccion).get("entradas", [])[: args.turnos]
    if not entradas:
        print("No hay ejecuciones anteriores: no hay nada que evitar.")
        return 0

    titulos = {}
    for entrada in entradas:
        ruta = carpeta_historico(args.seccion) / entrada["fichero"]
        if not ruta.exists():
            continue
        datos = leer_json(ruta)
        for clave in ("destacadas", "titulares", "noticias"):
            for noticia in datos.get(clave, []):
                if noticia.get("enlace"):
                    titulos.setdefault(noticia["enlace"], noticia.get("titulo", ""))

    print(f"Ya publicado en los ultimos {len(entradas)} turnos "
          f"({len(titulos)} noticias). No repitas nada de esto, ni la misma "
          f"noticia contada por otro medio con otro titular:\n")
    for enlace, titulo in titulos.items():
        print(f"- {titulo}\n  {enlace}")
    return 0


# --------------------------------------------------------------------------
# validar: comprueba lo comprobable del JSON recien escrito
# --------------------------------------------------------------------------

class Revision:
    def __init__(self):
        self.errores = []
        self.avisos = []

    def error(self, texto):
        self.errores.append(texto)

    def aviso(self, texto):
        self.avisos.append(texto)


def validar_fecha(valor, formato):
    try:
        return datetime.strptime(valor, formato)
    except (TypeError, ValueError):
        return None


def validar_noticia(rev, noticia, indice, es_destacada, momento):
    etiqueta = f"{'destacada' if es_destacada else 'titular'} {indice + 1}"
    campos = ["titulo", "fuente", "enlace", "fecha"]
    if es_destacada:
        campos.append("resumen")

    for campo in campos:
        if not str(noticia.get(campo, "")).strip():
            rev.error(f"{etiqueta}: le falta el campo '{campo}' o esta vacio.")

    if not es_destacada and "resumen" in noticia:
        rev.error(f"{etiqueta}: los titulares no llevan 'resumen'. Se quita.")

    enlace = str(noticia.get("enlace", ""))
    if enlace and not enlace.startswith(("http://", "https://")):
        rev.error(f"{etiqueta}: el enlace no es una URL completa: {enlace}")

    fuente = str(noticia.get("fuente", ""))
    if "/" in fuente or " y " in fuente.lower() or "segun" in fuente.lower():
        rev.error(f"{etiqueta}: 'fuente' es el nombre de UN medio, tal cual. "
                  f"Ni dos medios, ni formulas: {fuente!r}")

    valor = str(noticia.get("fecha", ""))
    if not valor:
        return

    if es_destacada:
        fecha = validar_fecha(valor, FORMATO_FECHA_HORA)
        if fecha is None:
            rev.error(f"{etiqueta}: la fecha debe ser 'DD-MM-AAAA HH:MM' "
                      f"(fecha y hora de publicacion del articulo): {valor!r}")
        elif momento and fecha > momento:
            rev.error(
                f"{etiqueta}: fecha posterior a la hora de ejecucion ({valor}). "
                f"Has cogido la fecha de lo que se cuenta dentro (un lanzamiento, "
                f"un evento) en vez de la fecha en que se publico el articulo."
            )
    else:
        if validar_fecha(valor, FORMATO_FECHA) is None:
            if validar_fecha(valor, FORMATO_FECHA_HORA):
                rev.error(f"{etiqueta}: los titulares llevan la fecha SIN hora, "
                          f"en formato DD-MM-AAAA: {valor!r}. Como no abres el "
                          f"articulo no puedes saber la hora de publicacion.")
            else:
                rev.error(f"{etiqueta}: la fecha debe ser 'DD-MM-AAAA': {valor!r}")
        elif momento and validar_fecha(valor, FORMATO_FECHA).date() > momento.date():
            rev.error(f"{etiqueta}: fecha posterior al dia de ejecucion ({valor}).")


def validar_reparto(rev, seccion, destacadas, titulares, turno):
    espanoles = medios_espanoles(seccion)
    min_medios = cupo(seccion, "min_medios", MIN_MEDIOS_TITULARES).get(turno, 5)

    def es_espanol(fuente):
        return str(fuente).strip().lower() in espanoles

    cuenta = Counter(n.get("fuente", "") for n in destacadas)
    for fuente, veces in cuenta.items():
        if veces > MAX_DESTACADAS_POR_MEDIO:
            rev.error(f"{veces} destacadas de {fuente}: el maximo es "
                      f"{MAX_DESTACADAS_POR_MEDIO}. Sustituye las que sobren por "
                      f"noticias de otros medios que hayas encontrado.")

    if destacadas and espanoles and not any(es_espanol(n.get("fuente")) for n in destacadas):
        aviso = cupo(seccion, "destacada_espanola", "error") == "aviso"
        (rev.aviso if aviso else rev.error)(
            "Ninguna destacada viene de un medio espanol. Tiene que haber "
            "al menos una." if not aviso else
            "Ninguna destacada viene de un medio espanol. En esta seccion es "
            "un aviso y no un error: sus medios espanoles publican poco y hay "
            "turnos en los que no hay ninguna. Comprueba que no se ha quedado "
            "un feed espanol caido antes de darlo por bueno.")

    cuenta = Counter(n.get("fuente", "") for n in titulares)
    for fuente, veces in cuenta.items():
        if veces > MAX_TITULARES_POR_MEDIO:
            rev.aviso(f"{veces} titulares de {fuente} (recomendado: "
                      f"{MAX_TITULARES_POR_MEDIO} como mucho). Suele significar "
                      f"que has consultado pocos medios.")

    if titulares and len(cuenta) < min_medios:
        plural = "medio distinto" if len(cuenta) == 1 else "medios distintos"
        rev.aviso(f"Solo {len(cuenta)} {plural} entre los titulares "
                  f"(esperados {min_medios} en el turno {turno}). Comprueba que "
                  f"'candidatos' no ha dejado feeds caidos sin mirar. Si de "
                  f"verdad no hay mas, se publica con lo que haya: es preferible "
                  f"a rellenar con guias u ofertas.")

    if titulares and espanoles and not any(es_espanol(n.get("fuente")) for n in titulares):
        rev.aviso("Ningun titular viene de un medio espanol.")


def validar_horas_inventadas(rev, destacadas):
    horas = [validar_fecha(str(n.get("fecha", "")), FORMATO_FECHA_HORA)
             for n in destacadas]
    horas = [h for h in horas if h and not (h.hour == 0 and h.minute == 0)]
    if len(horas) >= 3 and all(h.minute == 0 for h in horas):
        rev.aviso("Todas las destacadas con hora la tienen en punto. Suele ser "
                  "senal de que se estan inventando: usa la hora que pone el "
                  "articulo, y 00:00 si no la indica.")


def cmd_validar(args):
    ruta = ruta_actual(args.seccion)
    rev = Revision()

    try:
        datos = leer_json(ruta)
    except FileNotFoundError:
        print(f"ERROR: no existe {ruta.relative_to(RAIZ)}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: {ruta.relative_to(RAIZ)} no es JSON valido: {e}")
        return 1

    if datos.get("seccion") != args.seccion:
        rev.error(f"El campo 'seccion' deberia ser '{args.seccion}' y es "
                  f"{datos.get('seccion')!r}.")

    momento = None
    actualizado = str(datos.get("actualizado", ""))
    momento = validar_fecha(actualizado, FORMATO_FECHA_HORA)
    if momento is None:
        rev.error(f"'actualizado' debe ser 'DD-MM-AAAA HH:MM' con la hora de "
                  f"ejecucion en hora espanola: {actualizado!r}")

    destacadas = datos.get("destacadas")
    titulares = datos.get("titulares")
    if not isinstance(destacadas, list) or not isinstance(titulares, list):
        print("ERROR: 'destacadas' y 'titulares' tienen que ser listas.")
        return 1

    for i, noticia in enumerate(destacadas):
        validar_noticia(rev, noticia, i, True, momento)
    for i, noticia in enumerate(titulares):
        validar_noticia(rev, noticia, i, False, momento)

    enlaces = [n.get("enlace") for n in destacadas + titulares if n.get("enlace")]
    for enlace, veces in Counter(enlaces).items():
        if veces > 1:
            rev.error(f"El enlace {enlace} aparece {veces} veces. Una noticia "
                      f"puede ser destacada o titular, no las dos.")

    # El turno propio se excluye: si esta ejecucion ya se archivo (o se esta
    # repitiendo el mismo turno), su copia esta en el historico y si no se
    # descarta sale el fichero entero marcado como repetido.
    propio = partir_actualizado(actualizado)[:2] if momento else (None, None)
    publicados = publicados_antes(args.seccion, excluir=propio)
    for enlace in enlaces:
        if enlace in publicados:
            rev.error(f"Ya se publico el {publicados[enlace]}: {enlace}")

    turno = propio[1] or "M"
    validar_reparto(rev, args.seccion, destacadas, titulares, turno)
    validar_horas_inventadas(rev, destacadas)

    if len(destacadas) < 5:
        rev.aviso(f"Solo {len(destacadas)} destacadas de 5.")
    minimo = cupo(args.seccion, "min_titulares", MIN_TITULARES).get(turno, 15)
    tope = cupo(args.seccion, "max_titulares", MAX_TITULARES)
    if len(titulares) < minimo:
        rev.aviso(f"Solo {len(titulares)} titulares (esperados {minimo} en el "
                  f"turno {turno}, tope {tope}). Repasa la salida de "
                  f"'candidatos': si algun feed fallo, vuelve a lanzarlo antes "
                  f"de darlo por bueno.")

    for texto in rev.errores:
        print(f"ERROR: {texto}")
    for texto in rev.avisos:
        print(f"AVISO: {texto}")

    if rev.errores:
        print(f"\n{len(rev.errores)} errores. Corrige el JSON y vuelve a validar.")
        return 1

    print(f"JSON correcto: {len(destacadas)} destacadas, {len(titulares)} "
          f"titulares." + (f" {len(rev.avisos)} avisos que revisar."
                           if rev.avisos else ""))
    return 0


# --------------------------------------------------------------------------
# archivar: copia del turno + entrada en el indice. Nunca borra
# --------------------------------------------------------------------------

def cmd_archivar(args):
    datos = leer_json(ruta_actual(args.seccion))
    try:
        fecha, turno, _ = partir_actualizado(str(datos.get("actualizado", "")))
    except ValueError:
        print("ERROR: 'actualizado' no tiene el formato 'DD-MM-AAAA HH:MM', "
              "asi que no se puede saber de que dia y turno es. Corrige "
              f"data/{args.seccion}.json y repite.")
        return 1

    nombre = f"{fecha}_{turno}.json"
    escribir_json(carpeta_historico(args.seccion) / nombre, datos)

    indice = leer_indice(args.seccion)
    entradas = [e for e in indice.get("entradas", [])
                if not (e.get("fecha") == fecha and e.get("turno") == turno)]
    repetido = len(entradas) != len(indice.get("entradas", []))
    entradas.insert(0, {
        "fecha": fecha,
        "turno": turno,
        "actualizado": datos["actualizado"],
        "fichero": nombre,
    })
    entradas.sort(key=lambda e: (e["fecha"], e["turno"]), reverse=True)
    indice["seccion"] = args.seccion
    indice["entradas"] = entradas
    escribir_json(carpeta_historico(args.seccion) / "indice.json", indice)

    # El indice de busqueda del mes al que pertenece este turno. Va aqui y no
    # en un comando aparte porque un buscador que no encuentra lo de hoy no es
    # medio buscador: es uno en el que se deja de confiar.
    indexadas = escribir_busqueda(args.seccion, mes_de(fecha))

    print(f"Archivado en data/historico/{args.seccion}/{nombre} "
          f"({'entrada actualizada' if repetido else 'entrada nueva'}). "
          f"El historico tiene {len(entradas)} turnos. "
          f"Buscador: {indexadas} noticias en {mes_de(fecha)}.")
    return 0


# --------------------------------------------------------------------------
# busqueda: el indice que hace consultable el historico
# --------------------------------------------------------------------------

def carpeta_busqueda(seccion):
    return carpeta_historico(seccion) / "busqueda"


def mes_de(fecha):
    """'2026-08-21' -> '2026-08'"""
    return str(fecha)[:7]


def escribir_busqueda(seccion, mes):
    """Rehace el indice de busqueda de un mes leyendo sus turnos archivados.

    Un fichero por mes y no uno solo con los 90 dias, y esto se midio: el
    indice crece a 24 KB al dia entre las tres secciones. Con un fichero unico,
    cada turno reescribe los 90 dias enteros y el repo engorda ~1,5 GB al ano;
    por meses solo se reescribe el mes en curso y baja a ~0,2 GB. La otra mitad
    de la razon es que un mes cerrado no se vuelve a tocar nunca.

    Se rehace entero en vez de anadir al final: leer los turnos del mes cuesta
    milisegundos, y asi el fichero se repara solo si un dia sale mal. Por eso
    mismo no lleva marca de tiempo dentro: sin ella, rehacerlo sin cambios deja
    el fichero identico y git no ve un cambio donde no lo hay.
    """
    entradas = [e for e in leer_indice(seccion).get("entradas", [])
                if mes_de(e.get("fecha", "")) == mes]
    entradas.sort(key=lambda e: (e["fecha"], e["turno"]), reverse=True)

    noticias, vistos = [], set()
    for entrada in entradas:
        ruta = carpeta_historico(seccion) / entrada["fichero"]
        if not ruta.exists():
            continue
        datos = leer_json(ruta)
        turno = f"{entrada['fecha']}_{entrada['turno']}"
        for noticia in ((datos.get("destacadas") or []) +
                        (datos.get("titulares") or [])):
            enlace = noticia.get("enlace") or ""
            # Si la misma noticia salio en dos turnos se queda la del mas
            # reciente: el buscador esta para encontrarla, no para contar
            # cuantas veces se publico.
            if enlace and enlace in vistos:
                continue
            if enlace:
                vistos.add(enlace)
            noticias.append({
                "titulo": noticia.get("titulo", ""),
                "fuente": noticia.get("fuente", ""),
                "fecha": noticia.get("fecha", ""),
                "enlace": enlace,
                "turno": turno,
            })

    escribir_json(carpeta_busqueda(seccion) / f"{mes}.json",
                  {"seccion": seccion, "mes": mes, "noticias": noticias})
    return len(noticias)


def cmd_indexar(args):
    """Rehace los indices de busqueda de una seccion, mes a mes.

    'archivar' ya mantiene el mes del turno que archiva, asi que esto es para
    sembrar una seccion que viene de antes del buscador, o para reparar.
    """
    meses = sorted({mes_de(e.get("fecha", ""))
                    for e in leer_indice(args.seccion).get("entradas", [])})
    if not meses:
        print(f"ERROR: '{args.seccion}' no tiene historico del que sacar un "
              "indice de busqueda. Comprueba que la seccion existe y que "
              f"data/historico/{args.seccion}/indice.json tiene entradas.")
        return 1

    total = 0
    for mes in meses:
        cuantas = escribir_busqueda(args.seccion, mes)
        total += cuantas
        print(f"  {mes}: {cuantas} noticias")
    print(f"{total} noticias indexadas en {len(meses)} "
          f"{'mes' if len(meses) == 1 else 'meses'} "
          f"({args.seccion}).")
    return 0


# --------------------------------------------------------------------------
# comprobar: que una seccion este dada de alta en todos los sitios
# --------------------------------------------------------------------------

def leer_secciones():
    return leer_json(SECCIONES).get("secciones", [])


def cmd_comprobar(args):
    """Cruza assets/secciones.json con el resto del repo.

    Dar de alta una seccion toca ocho sitios, y olvidarse de uno no rompe nada
    de forma visible: sin su bloque en historico.html la seccion funciona pero
    no tiene dias anteriores, y sin el 'desde' de su indice 'estado' reclama
    turnos de antes de que existiera. Los dos fallos aparecen semanas despues.
    Esto los convierte en un mensaje.
    """
    secciones = leer_secciones()
    if not secciones:
        print(f"ERROR: {SECCIONES.name} no tiene ninguna seccion. Sin esa "
              "lista, el historico se queda sin pestanas y el icono sin "
              "colores.")
        return 1

    rev = Revision()
    portada = (RAIZ / "index.html").read_text(encoding="utf-8")
    css = (RAIZ / "assets" / "estilo.css").read_text(encoding="utf-8")
    medios = leer_json(MEDIOS).get("secciones", {})

    for seccion in secciones:
        ident = seccion.get("id", "")
        acento = seccion.get("acento", "")
        quien = f"'{ident}'"

        if not (RAIZ / f"{ident}.html").exists():
            rev.error(f"{quien}: falta {ident}.html. Copia el de otra seccion, "
                      "cambia el titulo, el data-seccion del <body> y la ruta "
                      "del JSON.")

        if not ruta_actual(ident).exists():
            rev.error(f"{quien}: falta data/{ident}.json, que es lo que pinta "
                      "la pagina. Hasta que la rutina escriba el primero, vale "
                      'uno con los dos arrays vacios.')

        # Dos veces en la portada: el chip de arriba y la entrada de abajo.
        enlaces = portada.count(f'href="{ident}.html"')
        if not enlaces:
            rev.error(f"{quien}: index.html no la enlaza. Sin chip ni entrada, "
                      "a la seccion no se llega desde la portada.")
        elif enlaces < 2:
            rev.aviso(f"{quien}: index.html la enlaza {enlaces} vez. Deberian "
                      "ser dos, el chip de arriba y la entrada de abajo.")

        for trozo, donde in ((f"--acento-{acento}:", "la variable de color"),
                             (f'body[data-seccion="{acento}"]', "el acento de la pagina"),
                             (f".{acento} ", "la clase de la portada")):
            if trozo not in css:
                rev.error(f"{quien}: falta {donde} en assets/estilo.css "
                          f"({trozo}). El CSS no lee este JSON, hay que "
                          "escribirlo a mano.")

        if seccion.get("tipo") == "noticias" and ident not in medios:
            rev.error(f"{quien}: no tiene medios en scripts/medios.json, asi "
                      "que 'candidatos' no sabria de donde sacar noticias.")

        if seccion.get("historico"):
            indice = carpeta_historico(ident) / "indice.json"
            if not indice.exists():
                rev.error(f"{quien}: falta data/historico/{ident}/indice.json. "
                          "Crealo con 'seccion', 'entradas': [] y un 'desde'.")
            else:
                datos = leer_json(indice)
                if not datos.get("entradas") and not datos.get("desde"):
                    rev.error(f"{quien}: su indice no tiene turnos ni 'desde'. "
                              "Sin 'desde', 'estado' reclama todos los turnos "
                              "anteriores a que la seccion existiera, y un "
                              "aviso que sale siempre se deja de leer.")

    # Y al reves: lo que hay en el repo y no en la lista.
    conocidas = {s.get("id") for s in secciones}
    for ident in medios:
        if ident not in conocidas:
            rev.aviso(f"scripts/medios.json tiene medios de '{ident}', que no "
                      f"esta en {SECCIONES.name}: nadie los va a leer.")

    if HISTORICO.exists():
        for carpeta in sorted(HISTORICO.iterdir()):
            if carpeta.is_dir() and carpeta.name not in conocidas:
                rev.aviso(f"data/historico/{carpeta.name}/ guarda turnos de una "
                          f"seccion que no esta en {SECCIONES.name}: no sale en "
                          "el historico de la web.")

    for texto in rev.errores:
        print(f"ERROR: {texto}")
    for texto in rev.avisos:
        print(f"AVISO: {texto}")

    if rev.errores:
        print(f"\n{len(rev.errores)} errores en el alta de las secciones.")
        return 1

    nombres = ", ".join(s.get("id", "?") for s in secciones)
    print(f"Las {len(secciones)} secciones estan completas: {nombres}." +
          (f" {len(rev.avisos)} avisos que revisar." if rev.avisos else ""))
    return 0


# --------------------------------------------------------------------------
# publicar: commit y push, con reintento si la rama ha avanzado
# --------------------------------------------------------------------------

def git(*args, comprobar=True):
    # encoding fijo y no el del sistema: 'estado' lee por aqui JSON con acentos,
    # y en Windows la salida saldria en cp1252 y los reventaria.
    return subprocess.run(["git", "-C", str(RAIZ)] + list(args),
                          capture_output=True, text=True, check=comprobar,
                          encoding="utf-8", errors="replace")


def falta_archivar(seccion):
    """Devuelve el motivo por el que la seccion no esta bien archivada, o None."""
    actual = ruta_actual(seccion)
    if not actual.exists():
        return None
    if not carpeta_historico(seccion).exists():
        # No todas las secciones llevan historico: ofertas, por ejemplo, guarda
        # su minimo dentro del propio JSON. Sin carpeta no hay nada que exigir.
        return None
    datos = leer_json(actual)
    try:
        fecha, turno, _ = partir_actualizado(str(datos.get("actualizado", "")))
    except ValueError:
        return "su campo 'actualizado' no tiene el formato 'DD-MM-AAAA HH:MM'"
    copia = carpeta_historico(seccion) / f"{fecha}_{turno}.json"
    if not copia.exists():
        return f"no existe su copia {copia.name} en el historico"
    if leer_json(copia) != datos:
        return f"su copia {copia.name} no coincide con lo que se va a publicar"
    return None


def cmd_publicar(args):
    # Solo data/: el HTML y el CSS no se tocan nunca, y asi no puede pasar
    # aunque una ejecucion los haya modificado por error.
    git("add", "--", "data")
    if not git("diff", "--cached", "--quiet", comprobar=False).returncode:
        print("No hay cambios en data/ que publicar.")
        return 0

    # Publicar sin archivar deja la web actualizada y el historico con un hueco,
    # y el hueco ya no se puede rellenar: la noticia vieja se ha sobrescrito.
    cambiados = git("diff", "--cached", "--name-only").stdout.split()
    for fichero in cambiados:
        partes = fichero.split("/")
        if len(partes) == 2 and partes[0] == "data" and partes[1].endswith(".json"):
            seccion = partes[1][: -len(".json")]
            motivo = falta_archivar(seccion)
            if motivo:
                print(f"ERROR: {seccion} sin archivar ({motivo}). Lanza "
                      f"'python3 scripts/noticias.py archivar {seccion}' y repite.")
                return 1

    git("commit", "-m", args.mensaje)

    # HEAD:main y no main a secas: las rutinas a veces trabajan con HEAD
    # desacoplado, y ahi 'push origin main' empuja la rama local vieja. Si
    # ademas coincide con la remota, git responde "up to date" y el push da
    # por bueno un commit que no ha subido.
    for intento in range(1, 4):
        if git("push", "origin", "HEAD:main", comprobar=False).returncode == 0:
            local = git("rev-parse", "HEAD").stdout.strip()
            git("fetch", "origin", "main", comprobar=False)
            remoto = git("rev-parse", "FETCH_HEAD", comprobar=False).stdout.strip()
            if local != remoto:
                print(f"ERROR: git ha aceptado el push pero origin/main sigue en "
                      f"{remoto[:7]} y el commit es {local[:7]}. No se ha "
                      f"publicado nada.")
                return 1
            print(f"Publicado en main como {local[:7]} (intento {intento}).")
            return 0
        print(f"Push rechazado (intento {intento}), reintentando con rebase...")
        rebase = git("pull", "--rebase", "origin", "main", comprobar=False)
        if rebase.returncode != 0:
            git("rebase", "--abort", comprobar=False)
            print("ERROR: el rebase ha dado conflicto. Resuelvelo a mano.")
            print(rebase.stdout + rebase.stderr)
            return 1

    print("ERROR: no se ha podido hacer push despues de 3 intentos.")
    return 1


# --------------------------------------------------------------------------
# estado: que turnos deberian estar publicados y cuales faltan
# --------------------------------------------------------------------------

def traer_remoto():
    """origin/main al dia, o None si no hay red.

    Se compara contra lo publicado, no contra la copia de trabajo: las rutinas
    corren en la nube y empujan alli, asi que un clon local sin actualizar no
    tiene los turnos de hoy y los daria por perdidos estando publicados.
    """
    if git("fetch", "origin", "main", comprobar=False).returncode != 0:
        return None
    return "FETCH_HEAD"


def leer_publicado(ruta, remoto):
    """Contenido de un fichero del repo en origin/main, o None si no esta."""
    if remoto is None:
        local = RAIZ / ruta
        if not local.exists():
            return None
        texto = local.read_text(encoding="utf-8")
    else:
        hecho = git("show", f"{remoto}:{ruta}", comprobar=False)
        if hecho.returncode != 0:
            return None
        texto = hecho.stdout
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return None


def secciones_con_historico(remoto):
    """Secciones que llevan historico, que son las que actualiza una rutina."""
    if remoto is None:
        if not HISTORICO.exists():
            return []
        return sorted(d.name for d in HISTORICO.iterdir() if d.is_dir())
    hecho = git("ls-tree", "--name-only", f"{remoto}:data/historico",
                comprobar=False)
    if hecho.returncode != 0:
        return []
    return sorted(n.rstrip("/") for n in hecho.stdout.split()
                  if not n.endswith(".json"))


def resumen_del_turno(seccion, entrada, remoto):
    """('04:12 (5+22)', vacio): a que hora salio el turno y cuanto trajo."""
    datos = leer_publicado(
        f"data/historico/{seccion}/{entrada.get('fichero', '')}", remoto)
    hora = str(entrada.get("actualizado", ""))[-5:] or "??:??"
    if datos is None:
        # El indice lo da por archivado pero su fichero no aparece. No es lo
        # mismo que faltar el turno, asi que se dice y no se cuenta como fallo.
        return f"{hora} (sin su fichero)", False
    destacadas = len(datos.get("destacadas", []))
    titulares = len(datos.get("titulares", []))
    # Un turno sin destacadas se publico, pero ese dia la web decia "todavia no
    # hay noticias". Se avisa y no se da por perdido: existe y esta archivado.
    return f"{hora} ({destacadas}+{titulares})", destacadas == 0


def cmd_estado(args):
    remoto = None if args.local else traer_remoto()
    if remoto is None and not args.local:
        print("# No se ha podido leer origin/main: se compara con la copia "
              "local, que puede ir por detras de lo que hayan publicado las "
              "rutinas. Un turno marcado como perdido puede estar sin traer.")

    secciones = secciones_con_historico(remoto)
    if not secciones:
        print("ERROR: no hay ninguna seccion con historico en data/historico/, "
              "asi que no hay turnos que comprobar.")
        return 1

    ahora = datetime.now(ESPANA)
    dias = [(ahora - timedelta(days=n)).strftime("%Y-%m-%d")
            for n in range(args.dias)]
    hoy = dias[0]

    donde = "la copia local" if remoto is None else "origin/main"
    print(f"Estado a {ahora.strftime(FORMATO_FECHA_HORA)} segun {donde}. "
          f"Entre parentesis, destacadas+titulares de cada turno.\n")

    perdidos, vacios = [], []
    for seccion in secciones:
        indice = leer_publicado(
            f"data/historico/{seccion}/indice.json", remoto) or {}
        turnos = {(e.get("fecha"), e.get("turno")): e
                  for e in indice.get("entradas", [])}
        # Una seccion recien abierta no tiene turnos perdidos detras: su rutina
        # no existia. Sin esto, el dia que se anadio 'ia' el comando pedia
        # explicaciones por los turnos de la semana anterior, y un aviso que
        # sale siempre y no significa nada es un aviso que se deja de leer.
        #
        # Admite dia ("2026-08-22") o dia y turno ("2026-08-21_T"), porque una
        # rutina nueva empieza a la hora que se cree, no a medianoche: 'ia'
        # arranco una tarde, y con la fecha a secas habia que elegir entre
        # reclamar su manana, que nunca existio, o no vigilar su primer turno.
        desde = indice.get("desde")
        print(seccion)
        for dia in dias:
            celdas = []
            for turno in ("M", "T"):
                entrada = turnos.get((dia, turno))
                if desde and (f"{dia}_{turno}" if "_" in desde else dia) < desde:
                    celdas.append(f"{turno} —")
                elif entrada:
                    texto, vacio = resumen_del_turno(seccion, entrada, remoto)
                    celdas.append(f"{turno} {texto}")
                    if vacio:
                        vacios.append((seccion, dia, turno))
                elif dia == hoy and ahora.hour < LIMITE_TURNO[turno]:
                    celdas.append(f"{turno} pendiente (hasta las "
                                  f"{LIMITE_TURNO[turno]}:00)")
                else:
                    celdas.append(f"{turno} FALTA")
                    perdidos.append((seccion, dia, turno))
            print(f"  {dia}  {celdas[0]:<26}{celdas[1]}")
        print()

    if vacios:
        print("AVISO: turnos publicados sin ninguna destacada. Ese dia la web "
              "decia 'todavia no hay noticias':")
        for seccion, dia, turno in vacios:
            print(f"- {seccion}, turno {turno} del {dia}.")
        print()

    if not perdidos:
        print("Todos los turnos que ya tocaban estan publicados.")
        return 0

    print(f"Falta{'n' if len(perdidos) > 1 else ''} "
          f"{len(perdidos)} turno{'s' if len(perdidos) > 1 else ''}:")
    for seccion, dia, turno in perdidos:
        cuando = "la manana" if turno == "M" else "la tarde"
        print(f"- {seccion}, turno {turno} ({cuando}) del {dia}.")
    print("\nEl log de cada ejecucion esta en https://claude.ai/code/routines. "
          "Un turno perdido no se recupera: los feeds solo dan lo reciente, "
          "asi que lo util es ver por que fallo antes del turno siguiente.")
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    ordenes = parser.add_subparsers(dest="orden", required=True)

    p = ordenes.add_parser("candidatos", help="titulares nuevos de los feeds")
    p.add_argument("seccion")
    p.add_argument("--horas", type=int, default=0,
                   help="mirar N horas atras en vez de desde el turno anterior")
    p.add_argument("--por-medio", type=int, default=12,
                   help="maximo de candidatos por medio")
    p.set_defaults(func=cmd_candidatos)

    p = ordenes.add_parser("titulares",
                           help="rellena los titulares de los medios espanoles")
    p.add_argument("seccion")
    p.add_argument("--horas", type=int, default=0,
                   help="mirar N horas atras en vez de desde el turno anterior")
    p.add_argument("--maximo", type=int, default=None,
                   help="tope de titulares del fichero, contando los que ya hay")
    p.add_argument("--probar", action="store_true",
                   help="ensenar lo que se anadiria sin escribir el fichero")
    p.set_defaults(func=cmd_titulares)

    p = ordenes.add_parser("anteriores", help="que se publico en turnos previos")
    p.add_argument("seccion")
    p.add_argument("--turnos", type=int, default=TURNOS_ANTERIORES)
    p.set_defaults(func=cmd_anteriores)

    p = ordenes.add_parser("validar", help="revisa el JSON recien escrito")
    p.add_argument("seccion")
    p.set_defaults(func=cmd_validar)

    p = ordenes.add_parser("archivar", help="copia el turno al historico")
    p.add_argument("seccion")
    p.set_defaults(func=cmd_archivar)

    p = ordenes.add_parser("indexar",
                           help="rehace el indice de busqueda del historico")
    p.add_argument("seccion")
    p.set_defaults(func=cmd_indexar)

    p = ordenes.add_parser("comprobar",
                           help="que las secciones esten dadas de alta enteras")
    p.set_defaults(func=cmd_comprobar)

    p = ordenes.add_parser("publicar", help="commit y push de data/")
    p.add_argument("mensaje")
    p.set_defaults(func=cmd_publicar)

    p = ordenes.add_parser("estado", help="que turnos faltan por publicar")
    p.add_argument("--dias", type=int, default=2,
                   help="dias hacia atras que se revisan, contando hoy")
    p.add_argument("--local", action="store_true",
                   help="no traer origin/main: mirar la copia de trabajo")
    p.set_defaults(func=cmd_estado)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
