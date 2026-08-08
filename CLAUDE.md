# Mi_Criadero

Web estatica de noticias publicada en **GitHub Pages**, cuyo contenido actualiza
sola una rutina programada de Claude en la nube.

- URL publica: https://spaizor.github.io/mi-criadero/
- Repositorio: https://github.com/spaizor/mi-criadero (rama `main`)

## Ojo: este proyecto NO sigue las reglas del contenedor

A diferencia del resto de carpetas de `c:\GitHub`, aqui **no hay Python, ni
`.venv`, ni `main.py`, ni empaquetado con PyInstaller**. Es HTML, CSS y JS
estatico. No busques un interprete ni intentes lanzarlo con `python main.py`.

Para verlo en local hace falta un servidor web (abrir el `index.html` con doble
clic falla por CORS al cargar los JSON):

```
python -m http.server 8765
```

## Idea clave: el HTML no se toca nunca

La estructura y el diseno se crearon una sola vez. Las tareas programadas
**solo reescriben un JSON** dentro de `data/`. Esto evita que una ejecucion
automatica rompa el diseno.

```
index.html            portada con los botones de seccion
tecnologia.html       seccion (carga data/tecnologia.json)
nintendo.html         seccion (carga data/nintendo.json)
ofertas.html          seccion (carga data/ofertas.json)
historico.html        dias anteriores (carga data/historico/)
assets/estilo.css     estilo compartido, claro/oscuro, responsive
assets/noticias.js    hace fetch del JSON y pinta las tarjetas
assets/ofertas.js     lo mismo para la seccion de precios
data/*.json           <-- lo unico que tocan las rutinas
data/historico/       <-- y su copia por turno, ver mas abajo
```

Al anadir una seccion nueva: copiar un HTML de seccion, cambiar el titulo, el
`data-seccion` del `<body>` (define el color de acento en el CSS) y la ruta del
JSON, y anadir su tarjeta en `index.html`. Para que salga tambien en el
historico hay que anadirla al array `SECCIONES` de `historico.html` y crear su
`data/historico/<seccion>/indice.json`.

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

## scripts/noticias.py

Todo el trabajo mecanico de las rutinas. La idea: una instruccion en el prompt
se paga en cada ejecucion y ademas puede olvidarse; un script no. Solo usa la
biblioteca estandar, porque el entorno de las rutinas no lo controlamos.

```
python3 scripts/noticias.py candidatos <seccion>   titulares nuevos, sacados de los RSS
python3 scripts/noticias.py anteriores <seccion>   lo ya publicado, para no repetirlo
python3 scripts/noticias.py validar    <seccion>   revisa el JSON recien escrito
python3 scripts/noticias.py archivar   <seccion>   copia del turno + indice
python3 scripts/noticias.py publicar   "<mensaje>" commit de data/ y push
```

- `validar` distingue **ERROR** (algo objetivamente mal: sale con codigo 1) de
  **AVISO** (sospechoso pero no invalido, normalmente haber consultado pocos
  medios). Los textos de error estan escritos para que se entiendan solos:
  ahi es donde viven ahora las explicaciones largas que antes ocupaban sitio
  en el prompt, y solo se pagan el dia que algo falla.
- `validar` compara con los turnos anteriores del historico **excluyendo el
  turno propio**; si no, una ejecucion ya archivada se marca entera como
  repetida.
- `archivar` es idempotente: repetir el mismo turno reescribe su fichero y
  actualiza su entrada, no anade una nueva. Nunca borra nada.
- `publicar` hace `git add` solo de `data/`. Asi el HTML y el CSS no pueden
  acabar en un commit automatico aunque una ejecucion los toque por error.
  Antes de hacer commit comprueba que cada seccion tocada tiene su copia en el
  historico: publicar sin archivar deja un hueco que ya no se puede rellenar,
  porque el JSON viejo se ha sobrescrito.
- `publicar` empuja con `git push origin HEAD:main`, no `origin main`. Las
  rutinas trabajan a veces con HEAD desacoplado, y ahi `origin main` empuja la
  rama local vieja; si ademas coincide con la remota, git responde "up to date"
  y da por publicado un commit que no ha subido. Despues del push compara el
  commit local con `origin/main` para no fiarse del codigo de salida.

Los limites de reparto (maximo por medio, minimo de medios) estan en las
constantes de arriba del script y **repiten los del prompt**: si se cambian en
un sitio, hay que cambiarlos en el otro. Los minimos son **por turno**: el de
tarde solo cubre desde la ejecucion de la manana, asi que exigirle lo mismo que
al de manana solo consigue que se rellene con guias y ofertas.

## scripts/medios.json y el comando `candidatos`

`medios.json` es la lista de medios por seccion, con su RSS. **No esta en
`data/`** a proposito: ahi lo publicaria `publicar` si una ejecucion lo tocara
por error. Solo se usan los medios con `"comprobado": true` y `feed` no nulo;
el resto se ignoran, asi que un medio roto nunca rompe una ejecucion.

`candidatos` descarga esos feeds y devuelve, en JSON, lo publicado **desde el
turno anterior** (fecha que saca del indice del historico), ya sin lo repetido
ni lo que huele a guia u oferta. De ahi salen los titulares: titulo, enlace y
fecha vienen del feed, no del criterio del modelo, que es justo donde antes se
inventaban las horas. El campo se llama `titulo_original` para que se note si
alguien lo copia sin traducir.

Las lineas que empiezan por `#` son el parte de la descarga y hay que leerlas:

- `FEED CAIDO <medio>`: no ha respondido esta vez. Reintentar suele bastar.
- `SIN FEED <medio>`: no tiene RSS utilizable y hay que abrirlo a mano. Ahora
  mismo son Vandal (su servidor corta la conexion a los scripts aunque el feed
  funcione en un navegador) y 3DJuegos (no publica RSS).

La lista es el **minimo**, no el techo: si un dia da poco, se busca ademas por
fuera. Y `candidatos` no cubre las 5 destacadas, que siguen exigiendo abrir y
leer el articulo.

## Formato de los JSON de contenido

Cada seccion tiene dos niveles: **5 destacadas** que la rutina abre y lee, y
hasta **25 titulares** que salen del listado del medio sin abrir el articulo.
Los titulares se pintan en un bloque plegable debajo de las destacadas.

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

Todas las fechas en hora espanola. **Los titulares llevan fecha sin hora a
proposito**: como no se abre el articulo, no hay forma de saber la hora de
publicacion, y pedirsela solo consigue que se la invente.

Si los dos arrays estan vacios, la pagina muestra un aviso de "todavia no hay
noticias" en lugar de romperse. `assets/noticias.js` acepta ademas el formato
antiguo (un unico array `noticias`) como respaldo, para que la web no se quede
en blanco entre un cambio de formato y la primera ejecucion de la rutina.

## La seccion de Ofertas

No busca ofertas: sigue el precio de una lista cerrada de productos, que vive
en `scripts/productos.json`. `scripts/precios.py consultar` abre cada ficha,
lee el precio y escribe `data/ofertas.json`. La rutina no elige nada, solo
lanza el script: por eso esta seccion cuesta una fraccion de lo que cuestan las
de noticias.

El precio **no se saca leyendo la pagina**, sino del bloque `schema.org/Product`
que las tiendas incrustan para Google. Las dos formas conviven y hay que cubrir
las dos: GAME lo publica en una etiqueta `<script type="application/ld+json">`
indentada, y MediaMarkt comprimido dentro del estado interno de la pagina, sin
etiqueta. Como una ficha trae ademas variantes y productos relacionados con sus
propios precios, se elige el bloque que contiene la referencia numerica de la
URL pedida.

Comprobado el 08-08-2026: **GAME y MediaMarkt** dejan pasar a un script. **El
Corte Ingles, Fnac, Carrefour e Idealo** responden 403. **Amazon queda fuera a
proposito**: bloquea scripts y su normativa lo prohibe. Antes de anadir una
tienda nueva al catalogo hay que pasarla por `precios.py probar <url>`.

Tres decisiones sobre no mentir en los precios:

- **Si una tienda no responde se conserva su ultimo precio** marcado como
  `viejo`, y la web avisa. Borrarlo dejaria un hueco; inventarlo seria peor.
- **`disponible` puede ser `null`**, que no es lo mismo que `false`. GAME no
  declara el stock: darlo por agotado seria publicar algo falso.
- **Se guarda el vendedor cuando la ficha lo dice.** En el marketplace de
  MediaMarkt el precio mas bajo suele ser de un tercero, no de la tienda.

El minimo historico vive dentro de `data/ofertas.json` y lo actualiza el script
comparando con la ejecucion anterior. Esta seccion **no usa `data/historico/`**,
y por eso `publicar` solo exige copia archivada a las secciones que tienen
carpeta ahi.

## Publicacion

GitHub Pages esta configurado como *Deploy from a branch* → `main` → `/ (root)`.
Cualquier push a `main` republica la web, pero **tarda 1-2 minutos**. Si un
cambio no se ve al instante, esperar antes de darlo por fallido.
