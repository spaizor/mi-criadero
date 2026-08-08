#!/usr/bin/env python3
"""Trabajo mecanico de las rutinas de noticias.

Todo lo que no requiere criterio vive aqui y no en el prompt: una instruccion
del prompt se paga en cada ejecucion, y ademas puede olvidarse. Un script no.

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
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HISTORICO = RAIZ / "data" / "historico"

# Turnos del historico que se miran para detectar noticias ya publicadas.
# 4 son dos dias: repetir algo de anteayer tambien es repetir.
TURNOS_ANTERIORES = 4

FORMATO_FECHA_HORA = "%d-%m-%Y %H:%M"
FORMATO_FECHA = "%d-%m-%Y"

MEDIOS_ESPANOLES = {
    "tecnologia": {"xataka", "genbeta", "hipertextual", "computerhoy",
                   "computer hoy", "adslzone"},
    "nintendo": {"nintenderos", "vandal", "3djuegos", "areajugones",
                 "hobbyconsolas"},
}

# Limites de reparto. Son los del prompt: si se cambian ahi, cambiarlos aqui.
MAX_DESTACADAS_POR_MEDIO = 2
MAX_TITULARES_POR_MEDIO = 5
MIN_MEDIOS_TITULARES = 5


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


# --------------------------------------------------------------------------
# anteriores: que se publico en los ultimos turnos, para no repetirlo
# --------------------------------------------------------------------------

def cmd_anteriores(args):
    indice = leer_indice(args.seccion)
    entradas = indice.get("entradas", [])[: args.turnos]

    if not entradas:
        print("No hay ejecuciones anteriores: no hay nada que evitar.")
        return 0

    vistos = {}
    for entrada in entradas:
        ruta = carpeta_historico(args.seccion) / entrada["fichero"]
        if not ruta.exists():
            continue
        datos = leer_json(ruta)
        for clave in ("destacadas", "titulares", "noticias"):
            for noticia in datos.get(clave, []):
                enlace = noticia.get("enlace")
                if enlace and enlace not in vistos:
                    vistos[enlace] = noticia.get("titulo", "")

    print(f"Ya publicado en los ultimos {len(entradas)} turnos "
          f"({len(vistos)} noticias). No repitas nada de esto, ni la misma "
          f"noticia contada por otro medio con otro titular:\n")
    for enlace, titulo in vistos.items():
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


def validar_reparto(rev, seccion, destacadas, titulares):
    espanoles = MEDIOS_ESPANOLES.get(seccion, set())

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

    if titulares and len(cuenta) < MIN_MEDIOS_TITULARES:
        plural = "medio distinto" if len(cuenta) == 1 else "medios distintos"
        rev.aviso(f"Solo {len(cuenta)} {plural} entre los titulares "
                  f"(recomendado: {MIN_MEDIOS_TITULARES}). Abre el listado de "
                  f"mas medios: el problema no es que el dia venga flojo.")

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
    previos = [e for e in leer_indice(args.seccion).get("entradas", [])
               if (e.get("fecha"), e.get("turno")) != propio]

    publicados = {}
    for entrada in previos[:TURNOS_ANTERIORES]:
        fichero = carpeta_historico(args.seccion) / entrada["fichero"]
        if fichero.exists():
            previo = leer_json(fichero)
            for clave in ("destacadas", "titulares", "noticias"):
                for noticia in previo.get(clave, []):
                    if noticia.get("enlace"):
                        publicados[noticia["enlace"]] = entrada["fecha"]
    for enlace in enlaces:
        if enlace in publicados:
            rev.error(f"Ya se publico el {publicados[enlace]}: {enlace}")

    validar_reparto(rev, args.seccion, destacadas, titulares)
    validar_horas_inventadas(rev, destacadas)

    if len(destacadas) < 5:
        rev.aviso(f"Solo {len(destacadas)} destacadas de 5.")
    if len(titulares) < 15:
        rev.aviso(f"Solo {len(titulares)} titulares (el tope son 25). Si no has "
                  f"abierto el listado de todos los medios, hazlo antes de darlo "
                  f"por bueno.")

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


def cmd_publicar(args):
    # Solo data/: el HTML y el CSS no se tocan nunca, y asi no puede pasar
    # aunque una ejecucion los haya modificado por error.
    git("add", "--", "data")
    if not git("diff", "--cached", "--quiet", comprobar=False).returncode:
        print("No hay cambios en data/ que publicar.")
        return 0

    git("commit", "-m", args.mensaje)

    for intento in range(1, 4):
        if git("push", "origin", "main", comprobar=False).returncode == 0:
            print(f"Publicado en main (intento {intento}).")
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
