#!/usr/bin/env python3
"""Trabajo mecanico de las rutinas de noticias.

Todo lo que no requiere criterio vive aqui y no en el prompt: una instruccion
del prompt se paga en cada ejecucion, y ademas puede olvidarse. Un script no.

    python3 scripts/noticias.py candidatos <seccion> [--horas N] [--por-medio N]
    python3 scripts/noticias.py anteriores <seccion> [--turnos N]
    python3 scripts/noticias.py validar    <seccion>
    python3 scripts/noticias.py archivar   <seccion>
    python3 scripts/noticias.py publicar   "mensaje de commit"

Solo biblioteca estandar: las rutinas corren en un entorno que no controlamos.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HISTORICO = RAIZ / "data" / "historico"
MEDIOS = Path(__file__).resolve().parent / "medios.json"

# Turnos del historico que se miran para detectar noticias ya publicadas.
# 4 son dos dias: repetir algo de anteayer tambien es repetir.
TURNOS_ANTERIORES = 4

FORMATO_FECHA_HORA = "%d-%m-%Y %H:%M"
FORMATO_FECHA = "%d-%m-%Y"

# Limites de reparto. Son los del prompt: si se cambian ahi, cambiarlos aqui.
MAX_DESTACADAS_POR_MEDIO = 2
MAX_TITULARES_POR_MEDIO = 5

# Minimos por turno. El turno de tarde solo puede coger lo publicado desde la
# manana, asi que exigirle lo mismo solo consigue que se rellene con paja.
MIN_TITULARES = {"M": 15, "T": 8}
MIN_MEDIOS_TITULARES = {"M": 5, "T": 3}

# Horas hacia atras que mira 'candidatos' cuando no hay turno anterior.
HORAS_POR_DEFECTO = 18

AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Titulares que no son noticia: guias, ofertas, listas y analisis. Se descartan
# antes de ensenarlos para que no acaben de relleno un dia flojo.
RUIDO = re.compile(
    r"^(como |cómo |guia|guía|analisis|análisis|review|top \d|los mejores|"
    r"las mejores|mejores |ofertas|chollo|ver online|donde ver|dónde ver)"
    r"|oferta|descuento|rebajad|precio m[ií]nimo|cupon|cupón",
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
                return respuesta.read(), None
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


def cmd_candidatos(args):
    medios = leer_medios(args.seccion)
    if not medios:
        print(f"ERROR: no hay medios comprobados para '{args.seccion}' en "
              f"scripts/medios.json. Repasa ese fichero.")
        return 1

    ahora = datetime.now(ESPANA)
    if args.horas:
        corte = ahora - timedelta(hours=args.horas)
        desde = f"ultimas {args.horas} h"
    else:
        entradas = leer_indice(args.seccion).get("entradas", [])
        previo = validar_fecha(entradas[0]["actualizado"], FORMATO_FECHA_HORA) if entradas else None
        if previo:
            corte = previo.replace(tzinfo=ESPANA)
            desde = f"turno anterior ({entradas[0]['actualizado']})"
        else:
            corte = ahora - timedelta(hours=HORAS_POR_DEFECTO)
            desde = f"ultimas {HORAS_POR_DEFECTO} h (no hay turno anterior)"

    ya_publicado = publicados_antes(args.seccion)

    candidatos, fallos, descartes = [], [], Counter()
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

        del_medio = []
        for titulo, enlace, fecha in entradas:
            if fecha is None or fecha < corte:
                descartes["viejas o sin fecha"] += 1
                continue
            if enlace in ya_publicado:
                descartes["ya publicadas"] += 1
                continue
            if RUIDO.search(titulo):
                descartes["guias, ofertas y analisis"] += 1
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
    for motivo, veces in descartes.most_common():
        print(f"# Descartadas {veces} por {motivo}.")
    for fallo in fallos:
        print(f"# FEED CAIDO {fallo}")
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
    min_medios = MIN_MEDIOS_TITULARES.get(turno, 5)

    def es_espanol(fuente):
        return str(fuente).strip().lower() in espanoles

    cuenta = Counter(n.get("fuente", "") for n in destacadas)
    for fuente, veces in cuenta.items():
        if veces > MAX_DESTACADAS_POR_MEDIO:
            rev.error(f"{veces} destacadas de {fuente}: el maximo es "
                      f"{MAX_DESTACADAS_POR_MEDIO}. Sustituye las que sobren por "
                      f"noticias de otros medios que hayas encontrado.")

    if destacadas and espanoles and not any(es_espanol(n.get("fuente")) for n in destacadas):
        rev.error("Ninguna destacada viene de un medio espanol. Tiene que haber "
                  "al menos una.")

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
    minimo = MIN_TITULARES.get(turno, 15)
    if len(titulares) < minimo:
        rev.aviso(f"Solo {len(titulares)} titulares (esperados {minimo} en el "
                  f"turno {turno}, tope 25). Repasa la salida de 'candidatos': "
                  f"si algun feed fallo, vuelve a lanzarlo antes de darlo por "
                  f"bueno.")

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

    print(f"Archivado en data/historico/{args.seccion}/{nombre} "
          f"({'entrada actualizada' if repetido else 'entrada nueva'}). "
          f"El historico tiene {len(entradas)} turnos.")
    return 0


# --------------------------------------------------------------------------
# publicar: commit y push, con reintento si la rama ha avanzado
# --------------------------------------------------------------------------

def git(*args, comprobar=True):
    return subprocess.run(["git", "-C", str(RAIZ)] + list(args),
                          capture_output=True, text=True, check=comprobar)


def falta_archivar(seccion):
    """Devuelve el motivo por el que la seccion no esta bien archivada, o None."""
    actual = ruta_actual(seccion)
    if not actual.exists():
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

    p = ordenes.add_parser("publicar", help="commit y push de data/")
    p.add_argument("mensaje")
    p.set_defaults(func=cmd_publicar)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
