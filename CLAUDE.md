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
python3 scripts/noticias.py titulares  <seccion>   rellena los titulares espanoles
python3 scripts/noticias.py anteriores <seccion>   lo ya publicado, para no repetirlo
python3 scripts/noticias.py validar    <seccion>   revisa el JSON recien escrito
python3 scripts/noticias.py archivar   <seccion>   copia del turno + indice
python3 scripts/noticias.py publicar   "<mensaje>" commit de data/ y push
python3 scripts/noticias.py estado                 que turnos faltan por publicar
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

### El comando `titulares`: los medios espanoles no pasan por el modelo

En un medio espanol **no hay nada que traducir**: el titulo del feed ya es
publicable. Hacerlo pasar por el modelo solo anadia el riesgo de siempre —
horas y fuentes inventadas— en la mitad del contenido. Asi que el reparto de
trabajo es ahora este:

1. `candidatos` da la materia prima.
2. El modelo escribe `data/<seccion>.json` con **las 5 destacadas y los
   titulares de los medios de fuera**, que si hay que traducir.
3. `titulares <seccion>` anade los de los medios `"idioma": "es"` leyendolos
   del feed, y reescribe el fichero.
4. `validar` -> `archivar` -> `publicar`, igual que antes.

Va despues de escribir el fichero y no antes porque necesita saber que ha
puesto el modelo: descarta por enlace contra las destacadas y contra los
titulares que ya haya, ademas de contra los turnos anteriores.

Lo que hay que saber para no romperlo:

- **El titulo se publica tal cual sale del feed.** El modelo hoy los reescribe
  un poco (de "El Galaxy S26 FE filtra todas sus caracteristicas" a "Se filtran
  todas las caracteristicas del Galaxy S26 FE"), y eso se pierde. Es un cambio
  aceptado, no un descuido: se cambia un retoque de estilo por la garantia de
  que el titular es el que publico el medio.
- **En tecnologia se pierde ademas al modelo como filtro de tema.** Colo un
  "Netflix confirma la proxima serie de Prime Video" de ADSLZone: `RUIDO` caza
  guias y ofertas, pero no lo que simplemente no viene a cuento. En nintendo
  eso lo tapa el filtro por tema; en tecnologia no, ver mas abajo.
- **Reparte uno de cada medio por vuelta**, no los 5 del primero que llega. Un
  feed largo como el de ComputerHoy se llevaria el hueco entero y el turno
  saldria con dos medios, que es justo lo que `validar` avisa.
- **Se planta si `data/<seccion>.json` es de un turno ya archivado.** Sin eso,
  una ejecucion en la que el modelo no llegase a escribir su fichero acabaria
  anadiendo las noticias de hoy al turno de ayer y publicandolo como nuevo.
- `--probar` ensena lo que anadiria sin tocar el fichero, y `--maximo` cambia
  el tope de 25 contando los que ya hay.

### El filtro por tema

Los medios generalistas de videojuegos colaban PlayStation, Xbox, Steam, anime
y cine en la seccion de Nintendo. Lo arregla el bloque `tema` de la seccion en
`medios.json`, que se aplica **solo a los medios con `"filtrar_tema": true`**.

**La regla es exigir el tema propio, no descartar la plataforma ajena.** Es al
reves de lo que parece y se decidio midiendo, no opinando:

- Descartando por "PS5, Xbox, Steam" pasaba todo lo que no nombra ninguna
  plataforma, que en un medio generalista es medio feed: de las 30 entradas de
  Areajugones solo caian 10, y lo que quedaba era manga, anime y Marvel.
- Exigiendo mencion de Nintendo caen 27 de 30 en Areajugones, 42 de 54 en
  HobbyConsolas y 93 de 100 en Eurogamer, y lo que queda es todo de la seccion.
- **Los multiplataforma no se pierden**, que era el miedo razonable: "El Senor
  de los Anillos ya esta disponible para PS5, Switch, Xbox y PC" nombra Switch,
  asi que entra. Por eso la lista `ajeno` que hubo al principio sobra.

**A los medios de Nintendo no se les aplica y no es un descuido**: sus noticias
dan la consola por sabida y no la nombran, asi que exigirsela tiraria la mitad
(5 de 9 en Nintenderos, 13 de 25 en Nintendo Life). El filtro es para los que
publican de todo, no para los especializados.

Se compara sin tildes en los dos lados, asi que da igual escribir "Pokemon" o
"Pokémon" en la lista. **Tecnologia no tiene `tema` a proposito**: "fuera de
tema" en una seccion de tecnologia general no se deja escribir como una lista
de palabras, y una lista a medias tiraria noticias buenas.

Los dos comandos que leen feeds (`candidatos` y `titulares`) aplican el filtro,
y tambien **descartan repetidos dentro de la misma ejecucion**: hay feeds que
publican la misma noticia dos veces (HobbyConsolas lo hace), asi que no basta
con mirar contra lo ya publicado. Se compara por enlace y, dentro de un mismo
medio, tambien por titulo.

#### Ampliar la lista `tema`: el peligro es colar, no quedarse corto

De 78 terminos que se propusieron de golpe una vez, **26 ya entraban solos**:
los terminos se cazan como palabra suelta *dentro* del titular, asi que
"Nintendo" ya cubre "Nintendo Direct" y "Nintendo Museum", "Mario" cubre "Paper
Mario" y "Mario Party", y "Wii" cubre "Wii U". Anadirlos no suma nada.

Y **7 eran peligrosos**, que es lo que importa: la mitad de los medios
filtrados son ingleses (Eurogamer solo trae 100 entradas al dia), asi que un
termino que ademas sea una palabra corriente deja pasar cualquier cosa.
"Mother" entra en *"A mother sues Roblox"*, "ARMS" en *"the best arms in the
meta"*, "DS" en *"Sony's DS controller patent"*, y lo mismo "Toad", "Peach",
"Ness" y "Labo". Contra los feeds de un dia no se disparo ninguno, pero eso fue
suerte de la muestra: hay que forzarlos a mano para verlo.

La salida es **cubrir la saga con un termino que no sea ambiguo**: "Earthbound"
en vez de "Mother", "Captain Toad" en vez de "Toad". Se gana lo mismo sin abrir
la puerta.

El procedimiento para meter uno nuevo es el de siempre en este proyecto,
medirlo: aplicarlo a los feeds y mirar **que titulares pasan a entrar que antes
no**. Si alguno no es de la seccion, el termino sobra. Los 37 que se anadieron
asi dieron +1 titular sobre 305 y ningun falso positivo, que es justo lo que se
busca: la lista no esta para pescar mas, sino para no perder un "Tears of the
Kingdom" que no diga "Zelda". El criterio esta tambien en `_instrucciones.tema`
de `medios.json`, que es donde se mira al editarlo.

### El comando `estado`

Contesta a la pregunta que antes habia que mirar a mano: **se ha publicado el
turno de hoy?** Recorre las secciones con historico y pinta, por dia y turno, la
hora a la que salio y cuanto trajo (`04:12 (5+22)` = 5 destacadas y 22
titulares). Sale con codigo 1 si falta algun turno, asi que sirve tal cual para
encadenarlo o lanzarlo desde un workflow.

Cuatro decisiones que lo hacen fiable:

- **Compara contra `origin/main`, no contra la copia de trabajo.** Las rutinas
  corren en la nube y empujan alli; un clon local sin traer no tiene los turnos
  de hoy y los daria por perdidos estando publicados. Se vio a la primera: la
  copia local no tenia el turno de tarde que si estaba en `origin`. Hace `git
  fetch` y lee con `git show FETCH_HEAD:<ruta>`. Si no hay red, avisa y usa lo
  local; `--local` fuerza ese modo.
- **Un turno no esta perdido hasta pasada su hora limite** (`LIMITE_TURNO`, 9:00
  y 21:00). Las rutinas salen a las 4:00 y 16:30, asi que hay margen de sobra
  para un reintento; sin esa espera el comando daria una falsa alarma cada
  manana y se dejaria de mirar.
- **Se cuentan las noticias de cada turno, no solo si existe.** Una ejecucion
  puede publicar y archivar un JSON vacio: ese dia la web dice "todavia no hay
  noticias" y el indice tan contento. Un turno con 0 destacadas sale como AVISO,
  no como error, porque publicado esta; los del 07-08-2026 son del montaje.
- **`--dias` cuenta hacia atras desde hoy**, por defecto 2: con eso, un fallo de
  la tarde se ve a la manana siguiente.

Como el turno perdido no se recupera (los feeds solo dan lo reciente), lo que
aporta el comando no es arreglarlo sino enterarse a tiempo de mirar el log en
https://claude.ai/code/routines antes del turno siguiente.

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
  mismo son Nintendo Wire (403 a los scripts hasta en la portada) y Meristation
  (su feed responde, pero la ultima entrada es de febrero de 2023).

La lista es el **minimo**, no el techo: si un dia da poco, se busca ademas por
fuera. Y `candidatos` no cubre las 5 destacadas, que siguen exigiendo abrir y
leer el articulo.

### Un medio "que bloquea a los scripts" casi nunca bloquea

Vandal estuvo meses fuera con la nota de que su servidor cortaba la conexion a
los scripts aunque el feed funcionase en un navegador. Era falso. Lo que manda
es el feed **con gzip sin que se lo pidan**, y como `descargar` no lo
descomprimia, lo que llegaba eran bytes binarios que el parser rechazaba como
XML invalido. Por eso `descargar` mira ahora el numero magico `1f 8b` ademas de
la cabecera `Content-Encoding`, que no todos la mandan bien.

3DJuegos estaba fuera con un "no publica RSS" sacado de probar `/rss/`,
`/rss.xml`, `/feed/` y `/noticias/rss/`. Si lo publica: en
**`/feedburner.xml`**, igual que Xataka, y **lo declara su propia portada**.
Adivinar rutas no lo iba a encontrar nunca; leer el HTML del medio, si.

Las dos lecciones valen para el proximo medio que parezca cerrado:

- **Antes de dar un medio por bloqueado, mirar que llega de verdad.** Un fallo
  de parseo no es un bloqueo, y los dos se cuentan igual en el parte. Volcar el
  tamano y los primeros bytes lo resuelve en un minuto.
- **La ruta del feed se lee, no se adivina.** Esta en el `<link>` de la portada
  o en el HTML; probar rutas a ciegas solo descarta las que se te ocurren.

Un 403 de verdad, ese si existe: Nintendo Wire lo da en las cuatro rutas **y en
la portada**, asi que ahi no es el feed ni la compresion.

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
lee el precio y escribe `data/ofertas.json`.

Como aqui no se elige nada, esta seccion **no la actualiza una rutina de Claude
sino `.github/workflows/precios.yml`**: lanza el script, y si ha entrado algun
precio publica reutilizando `noticias.py publicar`. Si no entra **ninguno**, no
publica y falla el job a proposito: seria un commit diario marcando todo como
viejo sin haber mirado nada, y ademas taparia el aviso de que las tiendas han
empezado a bloquear al runner.

El precio **no se saca leyendo la pagina**, sino del bloque `schema.org/Product`
que las tiendas incrustan para Google. Las dos formas conviven y hay que cubrir
las dos: GAME lo publica en una etiqueta `<script type="application/ld+json">`
indentada, y MediaMarkt comprimido dentro del estado interno de la pagina, sin
etiqueta. Como una ficha trae ademas variantes y productos relacionados con sus
propios precios, se elige el bloque que contiene la referencia numerica de la
URL pedida.

### Un 403 no dice que la tienda este cerrada

Durante dos dias se dio por hecho que MediaMarkt y PcComponentes filtraban las
**IP de datacenter**: daban precio desde casa y 403 desde el runner, y de ahi
salio `solo_enlace`. Era falso, y la forma de verlo fue pedir la misma ficha
**dos veces desde el mismo sitio y en el mismo segundo**, una con `urllib` y
otra con Chromium. Medido el 10-08-2026 desde el runner:

| Tienda | urllib | Chromium | En el catalogo |
|---|---|---|---|
| GAME | 59,99 EUR | 59,99 EUR | si, sin navegador |
| MediaMarkt | 403 | **50,99 EUR** | si, con `navegador` |
| PcComponentes | 403 | **50,99 EUR** (403 en 1 de 3) | si, con `navegador` |
| Xtralife | pagina sin precio | **52,95 EUR** | si, con `navegador` |
| Carrefour | 403 | **50,99 EUR** | si, con `navegador` |
| El Corte Ingles, Fnac | 403 | 403 | no |

Lo que filtran es **parecer un script**, no la direccion. Misma IP, mismo
minuto, distinto resultado: eso descarta la IP como explicacion. La leccion
util es que un 403 mide *como* pides, no si te dejan; antes de descartar una
tienda hay que repetir con `--navegador`. De las cinco descartadas con la
teoria vieja, Carrefour cayo a la primera.

**El Corte Ingles y Fnac si estan cerradas de verdad**: 403 en local y en el
runner con Chromium, y eso ya es tras los tres reintentos. Ahi hay deteccion
mas alla del User-Agent. Aun asi **El Corte Ingles esta en el catalogo con
`solo_enlace`**: no dara precio nunca, pero interesa tener el enlace a un clic.
Worten e Idealo quedan fuera por decision del usuario; Idealo ademas es un
comparador y mezcla tiendas digitales, que no es lo que se sigue aqui.

**Amazon sigue fuera, y esto no lo cambia**: su normativa lo prohibe, que no es
un obstaculo tecnico.

**Xtralife necesita el navegador por otro motivo**: no bloquea a nadie, monta
el bloque `Product` con JavaScript, asi que a `urllib` le llega la ficha sin
precio. Su dominio bueno es **`.com`**; `xtralife.es` es otro sitio, y probar
alli dio un "no publica precio" que no decia nada de esta tienda.

El coste de abrir Chromium (unos segundos por ficha) solo lo pagan las tiendas
marcadas: GAME responde a `urllib` en milisegundos y no tiene por que. El
navegador se abre **una vez por ejecucion** y se reaprovecha; arrancarlo es lo
caro, cada pagina despues sale casi gratis.

Esto rompe el "solo biblioteca estandar" que si cumple `noticias.py`:
`precios.py` necesita **Playwright** para las tiendas marcadas, y el workflow
lo instala. Si falta, el error lo dice con el comando para instalarlo. Para
probar en local: `pip install playwright && playwright install chromium`.

**La cadencia sigue siendo una vez al dia.** Lo que hace que esto funcione es
pasar por una visita normal; consultar cada media hora dejaria de serlo, y para
precios de videojuegos no aportaria nada.

**PcComponentes escribe `"@type": "product"` en minuscula.** Por eso
`es_producto()` compara sin mayusculas y aceptando lista: exigir la forma
exacta del estandar tiraba una ficha que traia el precio perfectamente.

**Un `AggregateOffer` no es una oferta, es el resumen de varias**, y su
`lowPrice` puede ser de otro vendedor. La ficha de The Adventures of Elliot en
PcComponentes resume dos ofertas con `lowPrice: 49` y `highPrice: 61.99`
cuando el precio de la tienda son los 61,99. Con Star Fox no se veia porque
`offerCount` era 1 y los dos valores coincidian: el fallo estaba ahi desde el
principio y solo aparecio al meter el segundo juego. `oferta_de()` busca ahora
la oferta cuya URL es la ficha pedida, y si no puede identificarla se queda con
`highPrice`: publicar de mas es un error que se ve al abrir la tienda, y
publicar de menos es un reclamo falso que nadie comprueba.

**Se reintenta tres veces, y no lo mismo en cada camino.** `traer()` (urllib)
reintenta los fallos de red pero **no** los HTTP: alli el 403 fue consistente y
repetirlo solo alarga la ejecucion. `Navegador.html()` **si** reintenta el 403,
porque el de PcComponentes resulto ser intermitente: 403 en una pasada y precio
quince minutos despues. Los dos casos son medidos, no simetricos por gusto.

**Hay tiendas que publican una cuota donde deberia ir el precio.** Orange
declara en su bloque `Product` un `"price": "2.07"` impecable de forma, pero es
la **cuota mensual sin IVA** de una financiacion a 24 meses. La cadena cuadra
entera: 59,99 / 1,21 / 24 = 2,07 (lo que declara) y 2,07 x 1,21 = 2,50 (lo que
pinta en pantalla). Sin darse cuenta, Orange habria salido en la web a 2,07 EUR
y coronada como la mas barata siendo de las mas caras.

El catalogo lo arregla con `"cuota": { "meses": 24 }`, y el script reconstruye
el contado. Tres cosas que hay que tener presentes:

- **El plazo no esta en la ficha.** Se dedujo probando plazos contra un PVP
  conocido; ahi no hay nada que leer, asi que lo pone el catalogo a mano.
- **El resultado no es exacto**: 2,07 x 1,21 x 24 = 60,11 y el PVP es 59,99.
  Los 12 centimos son el redondeo de la cuota a dos decimales.
- Por eso el registro lleva `"estimado"` y **la web lo dice** con su etiqueta.
  Un precio calculado por nosotros no puede presentarse igual que uno leido.

**Y una red por si aparece otro Orange.** El caso se caza a mano una vez, pero
las fichas no se leen todos los dias, asi que `descartar_absurdos()` lo
automatiza: un precio por debajo del **25% de la mediana del dia** no se
publica, se degrada como un fallo y el parte explica que mirar. Detalles que
importan:

- **Mediana y no media**, porque el valor absurdo arrastraria la media hacia
  abajo y podria acabar tapandose a si mismo.
- **El 25% no toca una rebaja de verdad**: probado con un -60%, que pasa. La
  cuota de Orange era el 4% del precio real, o sea que cae con mucho margen.
- **Con menos de tres precios no se juzga**: el raro podria ser justo el que
  marca la referencia.
- Se compara contra los precios del mismo dia, no contra un umbral fijo, para
  que valga igual con un juego de 60 EUR que con uno de 3.

**"No trae bloque de producto" puede querer decir que la tienda se ha caido.**
Xtralife empezo a fallar a menudo al crecer el catalogo y parecia que nos
estuviera limitando por pedirle varias fichas seguidas. No era eso: **devuelve
502 Bad Gateway** cada pocas cargas. Lo que despista es que la peticion inicial
responde 200 y la pagina **navega despues** a la de error, asi que el estado no
lo delata y lo que queda es una pagina sin bloque. Por eso `ERROR_DE_SERVIDOR`
mira el titulo: sin eso, el sondeo se pasaba su margen entero esperando un
bloque en una pagina que solo decia "502 Bad Gateway".

La leccion es que un fallo de la tienda se disfrazaba de fallo nuestro. Antes
de dar por buena una explicacion de este tipo hay que **mirar que llega**: se
vio cargando la ficha y volcando tamano, titulo y bloques cada pocos segundos.

Aun asi las visitas a una misma tienda van espaciadas (`PAUSA_MISMA_TIENDA`),
que con la cadencia diaria no cuesta nada y evita encadenarle peticiones.

**Al navegador se le espera al bloque, no un rato fijo.** Xtralife fallaba a
veces con "no trae ningun bloque de producto": el JavaScript no habia acabado.
Se sondea la pagina hasta que el bloque aparece, con un tope de 20 segundos, y
se sale en cuanto esta. Al sondear hay que tragarse el "the page is navigating
and changing the content" de `content()`: significa haber preguntado mientras
la ficha navegaba, no que la tienda falle. Solo aparecio en el runner, donde la
red va distinto, y tumbo a Xtralife los tres intentos. Preguntar por el dato y no por un elemento del DOM hace
que sirva para las dos formas de publicarlo, la etiqueta de GAME y el estado
interno de MediaMarkt. De paso la ejecucion entera bajo de unos 20 segundos a
menos de 10, porque las fichas rapidas ya no esperan de balde.

Seis decisiones sobre no mentir en los precios:

- **`"solo_enlace": true` es para las que no responden ni con navegador.** No
  se consultan (un fallo que se sabe seguro solo ensucia el parte y hace dudar
  de los que si importan) pero la web las pinta con su hipervinculo, y con su
  ultimo precio fechado si alguna vez se les saco. Puede no haberlo habido
  nunca, como en El Corte Ingles: entonces se pinta "Ver en la tienda" y ya.
  Mientras una tienda responda, lo correcto es consultarla, no guardarle sitio.
- **Solo los precios en estado `ok` compiten por "Mas barato".** Comparar uno
  de hace dias con uno de hoy y coronarlo seria dar por hecha una comparacion
  que nadie ha hecho.

- **Si una tienda no responde se conserva su ultimo precio** marcado como
  `viejo`, y la web avisa. Borrarlo dejaria un hueco; inventarlo seria peor.
- **`disponible` puede ser `null`**, que no es lo mismo que `false`. GAME no
  declara el stock: darlo por agotado seria publicar algo falso.
- **Se guarda el vendedor cuando la ficha lo dice.** En el marketplace de
  MediaMarkt el precio mas bajo suele ser de un tercero, no de la tienda.
- **Un precio reconstruido se marca como tal.** Los de `"cuota"` salen con su
  etiqueta de estimado y el calculo a la vista, para que se pueda comprobar.

El minimo historico vive dentro de `data/ofertas.json` y lo actualiza el script
comparando con la ejecucion anterior. Esta seccion **no usa `data/historico/`**,
y por eso `publicar` solo exige copia archivada a las secciones que tienen
carpeta ahi.

### Como lo pinta `assets/ofertas.js`

El JSON no cambia; lo que sigue son decisiones de la web, y las dos primeras
son la misma idea que las de arriba llevada al diseno:

- **Los precios de hoy van juntos y arriba, ordenados de mas barato a mas
  caro; los `viejo`, detras.** Intercalar uno de hace dias entre dos de hoy lo
  haria parecer igual de comparable de un vistazo, que es lo mismo que ya evita
  el que solo los `ok` compitan por "Mas barato".
- **Las tiendas sin precio se agrupan abajo en pequeno** ("Tambien a la venta
  en"). Ocupando una fila entera como las demas parecian tener algo que
  comparar, y no lo tienen; a un clic siguen estando.
- **El minimo historico solo se pinta cuando el precio de hoy esta por
  encima.** Como los precios casi nunca bajan, decir "es el minimo que hemos
  visto" salia en 18 de 24 filas: lo que aparece en todas partes no informa, y
  encima tapaba la unica fila que si habia estado mas barata alguna vez.
- **Se pinta la diferencia contra el mas barato** (`+9,00 €`). Es la
  comparacion a la que se entra, y ahorra restar de cabeza; cuando dos tiendas
  salen a `+0,09 €` se ve solo que da igual cual elegir.

Empatar es normal (tres tiendas a 50,99), asi que puede haber varias filas
marcadas como mas baratas a la vez. Es correcto, no un fallo del reparto.

## Publicacion

GitHub Pages esta configurado como *Deploy from a branch* → `main` → `/ (root)`.
Cualquier push a `main` republica la web, pero **tarda 1-2 minutos**. Si un
cambio no se ve al instante, esperar antes de darlo por fallido.
