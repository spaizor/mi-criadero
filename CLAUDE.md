# Mi_Criadero

Web estatica de noticias publicada en **GitHub Pages**, cuyo contenido actualiza
sola una rutina programada de Claude en la nube.

- URL publica: https://spaizor.github.io/mi-criadero/
- Repositorio: https://github.com/spaizor/mi-criadero (rama `main`)

Este fichero son las reglas. **El porque de cada decision, con sus mediciones,
esta en `docs/`** (indice al final). Antes de cambiar algo que aqui sale como
"no deshacer", leer su pagina: casi todo lo que parece mejorable ya se probo.

## Ojo: este proyecto NO sigue las reglas del contenedor

A diferencia del resto de carpetas de `c:\GitHub`, aqui **no hay `.venv`, ni
`main.py`, ni empaquetado con PyInstaller**. La web es HTML, CSS y JS estatico;
los scripts de `scripts/` son Python pero de biblioteca estandar (salvo
`precios.py`, que usa Playwright). No intentes lanzarlo con `python main.py`.

Para verlo en local hace falta un servidor web (abrir el `index.html` con doble
clic falla por CORS al cargar los JSON):

```
python -m http.server 8765
```

## Idea clave: el HTML no se toca nunca

La estructura y el diseno se crearon una sola vez. Las tareas programadas
**solo reescriben JSON** dentro de `data/`. Esto evita que una ejecucion
automatica rompa el diseno.

```
index.html            portada con los botones de seccion
tecnologia.html       seccion (carga data/tecnologia.json)
ia.html               seccion (carga data/ia.json)
nintendo.html         seccion (carga data/nintendo.json)
geopolitica.html      seccion (carga data/geopolitica.json)
ofertas.html          seccion (carga data/ofertas.json)
steam.html            seccion (carga data/steam.json)
historico.html        dias anteriores (carga data/historico/)
assets/estilo.css     estilo compartido, claro/oscuro, responsive
assets/noticias.js    hace fetch del JSON y pinta las tarjetas
assets/ofertas.js     lo mismo para la seccion de precios
assets/steam.js       lo mismo para Steam; se apoya en ofertas.js
assets/secciones.json la lista de secciones (historico, icono, comprobar)
assets/version.json   el numero de version del pie y sus cambios
data/*.json           <-- lo unico que tocan las rutinas
data/historico/       <-- y su copia por turno, ver mas abajo
scripts/              el trabajo mecanico (noticias, precios, steam, icono)
docs/                 el porque de cada decision
```

### Dar de alta una seccion

Toca **ocho sitios** y olvidar uno no rompe nada visible: su HTML (titulo,
`data-seccion` del `<body>` y ruta del JSON), el chip y la entrada de
`index.html`, sus reglas de `estilo.css` (`--acento-<acento>`), su entrada en
`assets/secciones.json` (con los `turnos` que publica), su bloque en
`scripts/medios.json` y su `data/historico/<seccion>/indice.json`.
**`python3 scripts/noticias.py comprobar` dice cual falta.**

Ese `indice.json` recien creado lleva **`"desde"`**, el primer turno que se le
va a pedir, como dia (`"2026-08-22"`) o dia y turno (`"2026-08-21_T"`). Sin eso
`estado` reclama turnos de antes de que la seccion existiera. Si la rutina se
crea mas tarde de lo previsto, hay que mover ese valor.

## Historico

Cada ejecucion guarda una copia de su JSON, ademas de en `data/<seccion>.json`,
en `data/historico/<seccion>/AAAA-MM-DD_<M|T>.json` (M = ejecucion de la manana,
T = de la tarde), y anade una entrada al principio de
`data/historico/<seccion>/indice.json`:

```json
{
  "seccion": "tecnologia",
  "entradas": [
    { "fecha": "2026-08-08", "turno": "M",
      "actualizado": "08-08-2026 06:15", "fichero": "2026-08-08_M.json" }
  ]
}
```

Tres decisiones que no hay que deshacer sin pensarlo:

- **Se escriben dos ficheros nuevos, no se renombra el anterior.** Renombrar
  primero y escribir despues deja una ventana en la que `data/<seccion>.json`
  no existe: si la rutina falla ahi, la web se queda rota.
- **Un indice por seccion**, no uno comun: asi cada rutina toca solo ficheros
  suyos y las dos no pueden pisarse.
- **Las rutinas no borran nada.** El historico solo crece; el limite de 90 dias
  lo aplica `historico.html` al pintar, no un borrado automatico.

El nombre del fichero va en orden ANO-MES-DIA (ordena solo alfabeticamente),
al reves que las fechas de dentro del JSON, que van en DD-MM-AAAA.

`archivar` mantiene ademas el indice del buscador en
`data/historico/<seccion>/busqueda/AAAA-MM.json` (ver `docs/noticias.md`).

## Formato de los JSON de contenido

Cada seccion tiene dos niveles: **7 destacadas** que la rutina abre y lee (6
en `ia`, 8 en `geopolitica`), y hasta **25 titulares** que salen del listado
del medio sin abrir el articulo. Los titulares se pintan en un bloque plegable
debajo de las destacadas.

```json
{
  "seccion": "tecnologia",
  "actualizado": "DD-MM-AAAA HH:MM",
  "destacadas": [
    {
      "titulo": "Titular en espanol",
      "resumen": "2-3 frases con los hechos concretos",
      "fuente": "Nombre del medio",
      "enlace": "https://...",
      "fecha": "DD-MM-AAAA HH:MM"
    }
  ],
  "titulares": [
    {
      "titulo": "Titular en espanol",
      "fuente": "Nombre del medio",
      "enlace": "https://...",
      "fecha": "DD-MM-AAAA"
    }
  ]
}
```

Todas las fechas en hora espanola. **El campo `actualizado` lo reescribe el
script** (`titulares` y `archivar`), asi que la hora que ponga ahi el modelo es
provisional. **Los titulares llevan fecha sin hora a proposito**: como no se
abre el articulo, no hay forma de saber la hora de publicacion, y pedirsela
solo consigue que se la invente.

Si los dos arrays estan vacios, la pagina muestra un aviso de "todavia no hay
noticias" en lugar de romperse. `assets/noticias.js` acepta ademas el formato
antiguo (un unico array `noticias`) como respaldo.

## Los scripts

```
python3 scripts/noticias.py candidatos <seccion>   titulares nuevos, sacados de los RSS
python3 scripts/noticias.py titulares  <seccion>   rellena los titulares espanoles
python3 scripts/noticias.py anteriores <seccion>   lo ya publicado, para no repetirlo
python3 scripts/noticias.py validar    <seccion>   revisa el JSON recien escrito
python3 scripts/noticias.py archivar   <seccion>   copia del turno + indice
python3 scripts/noticias.py indexar    <seccion>   rehace el indice del buscador
python3 scripts/noticias.py comprobar              secciones dadas de alta enteras
python3 scripts/noticias.py publicar   "<mensaje>" commit de data/ y push
python3 scripts/noticias.py estado                 que turnos faltan por publicar
python3 scripts/noticias.py vigilar                las tres comprobaciones, desde la rutina

python3 scripts/precios.py  consultar | probar | frescura | tiendas | sembrar | lanzar
python3 scripts/steam.py    consultar | probar <appid> | probar-ig <id> | descubrir | frescura
python3 scripts/iconos.py                          regenera los iconos (favicon, PNG, SVG)
```

Quien lanza que: las **noticias** las lanzan rutinas de Claude (prompts en
https://claude.ai/code/routines). **Ofertas, Steam, vigilancia y limpieza de
ramas** son workflows de `.github/workflows/`, sin Claude de por medio. La
rutina de vigilancia solo lanza `noticias.py vigilar`.

## Reglas que no hay que deshacer sin leer su pagina

**Principios del proyecto** (salen en todas las paginas de `docs/`):

- **Medir antes de decidir**, y medir sobre la materia prima (el feed, la
  portada de la categoria), no solo sobre lo ya publicado, que es una muestra
  sesgada.
- **Un dato que el script puede leer no se le pide al modelo**: titulares
  espanoles, horas, enlaces, `actualizado`.
- **Un aviso que sale siempre se deja de leer.** Antes de anadir un aviso,
  comprobar que no saltara a diario sin significar nada.
- **Convertir fallos mudos en ruidosos**: un job que falla manda correo; uno que
  se cuelga, o un cron que no dispara, no avisa.
- Solo biblioteca estandar en los scripts (menos `precios.py`), porque el
  entorno de las rutinas no lo controlamos.

**Noticias** (`docs/noticias.md`, `docs/filtros.md`, `docs/medios.md`):

- `publicar` hace `git add` solo de `data/`, exige copia archivada y empuja con
  `git push origin HEAD:main` (no `origin main`: HEAD puede estar desacoplado).
- Los titulares de medios `"idioma": "es"` se publican **tal cual el feed**; no
  pasan por el modelo.
- Los limites de reparto (`MIN_TITULARES`, `CUPOS`, tope por medio) de
  `noticias.py` **repiten los del prompt** de las rutinas: cambiar los dos.
- `tema` **exige el tema propio**, no descarta plataformas ajenas; no se aplica
  a los medios especializados de Nintendo; tecnologia no lleva `tema`.
- Contra el ruido: primero `excluir_rutas` (categoria de la URL), y solo si la
  categoria mezcla, `excluir_en_ruta`. **`adslzone.net/noticias/streaming-tv/`
  no se excluye entera**, ni `Cultura` en teleSUR/Prensa Latina, ni
  `/es/turkiye/` en Anadolu.
- Un termino de `tema` se mete midiendo que titulares pasan a entrar; nada de
  palabras corrientes en ingles ("Mother", "ARMS", "DS").
- Un medio "que bloquea" casi nunca bloquea: mirar los bytes que llegan (gzip)
  y leer la ruta del feed en su portada, no adivinarla. En robots.txt veta la
  **prohibicion general de automatizar**, no el bloqueo por nombre de
  rastreador.

**Secciones** (`docs/seccion-*.md`):

- IA: la lista `propio` va **sin "Nvidia"**; `tema_ajeno` de tecnologia
  **apunta** a la lista de `ia`, no la copia.
- Geopolitica: **sin filtro geografico** (se prioriza en las destacadas); sale
  una vez al dia y lo declara en `secciones.json`.
- Ofertas: anadir un producto es **push de `productos.json` y lanzar `Precios`
  a mano**. Amazon es `solo_enlace` y **no se asciende** aunque responda. Solo
  los precios `ok` compiten por "Mas barato". Nada de `channel="chrome"`.
  Orange publica una cuota: ojo con el plazo si baja de golpe.
- Steam: **no hay SteamID en el repo** (catalogo congelado); la clave de ITAD
  va en cabecera, nunca en la URL; los bundles se anaden a mano; `cc=es` y la
  comprobacion de EUR no se quitan.
- En los workflows, un `if` sobre la salida de un paso que puede saltarse
  **mira tambien si el paso corrio** (`''` y `'0'` valen igual en GitHub).

## Version

La version vive **solo en `assets/version.json`** y sube una decima por
**seccion nueva**. No se sube por cuenta propia: esperar a que se pida. Los
cambios del panel se escriben para quien usa la web, no para quien la programa.
Detalle en `docs/web.md`.

## Indice de `docs/`

| Pagina | Que cuenta |
|---|---|
| `docs/noticias.md` | `noticias.py`: `titulares`, `actualizado`, `estado`, buscador del historico |
| `docs/filtros.md` | `tema`, `excluir_rutas`, `excluir_en_ruta`, con sus mediciones |
| `docs/medios.md` | `medios.json`, `candidatos`, medios "bloqueados" y robots.txt |
| `docs/seccion-ia.md` | por que existe IA, sus cupos y como se separa de tecnologia |
| `docs/seccion-geopolitica.md` | medios, turnos, por que no hay filtro, `excluir_categorias` |
| `docs/seccion-ofertas.md` | tiendas, 403, navegador, objetivos, serie, como se pinta |
| `docs/seccion-steam.md` | API de Steam, ediciones, bundles, ITAD, Instant Gaming |
| `docs/vigilancia.md` | `vigilancia.yml`, `frescura`, repescas, `vigilar`, `comprobar` |
| `docs/icono.md` | icono, manifest y previsualizacion |
| `docs/web.md` | `serie_desde` y el numero de version del pie |
| `docs/ramas.md` | las ramas `claude/*` que dejan las rutinas y su limpieza |

Al documentar una decision nueva: va en su pagina de `docs/`, y aqui solo si
cambia una regla.

## Publicacion

GitHub Pages esta configurado como *Deploy from a branch* → `main` → `/ (root)`.
Cualquier push a `main` republica la web, pero **tarda 1-2 minutos**. Si un
cambio no se ve al instante, esperar antes de darlo por fallido. Lo que haya en
el repositorio, `docs/` y este fichero incluidos, lo sirve la web.
