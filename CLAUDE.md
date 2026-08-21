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
ia.html               seccion (carga data/ia.json)
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

Ese indice recien creado lleva **`"desde": "AAAA-MM-DD"`**, la fecha del primer
turno que se le va a pedir. Sin eso, `estado` reclama los turnos de los dias
anteriores a que la seccion existiera, y un aviso que sale siempre y no
significa nada es un aviso que se deja de leer. Si la rutina se crea mas tarde
de lo previsto, hay que mover esa fecha.

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

### El filtro por seccion de la URL: `excluir_rutas`

Con dos semanas de historico (1.211 noticias publicadas entre el 08 y el
21-08-2026) ya se podia medir que ruido quedaba en vez de imaginarlo, que era
lo que se estaba esperando. En nintendo casi nada: 1 publirreportaje en 531.
En tecnologia el ruido que quedaba **no era de titulares sueltos, eran dos
categorias enteras**:

- `hipertextual.com/cine-television/` puso **23 titulares**, todos de cine y
  series ("Las cinco mejores sitcom de los 2000", "3 razones para ver..."). Es
  el **28%** de lo que aporta Hipertextual, y el dia que se midio su feed traia
  6 de 15 entradas de ahi.
- `adslzone.net/ofertas/` puso **8**, todos de compra ("AliExpress hunde el
  precio de la tablet de Xiaomi"). `RUIDO` no los cazaba porque no dicen
  "oferta" ni "descuento" en el titular.

Los 31 eran ruido: **ni uno era noticia de la seccion**. Por eso el filtro no
mira el titular sino el enlace: **no se adivina de que va la noticia, se lee la
categoria en la que el propio medio la ha colgado**. Asi no puede haber falsos
positivos, que es el peligro de siempre de una lista de terminos, y no hay que
elegir palabras: el trabajo ya lo hizo el redactor al archivarla.

Lo que hay que saber para usarlo:

- **Solo sirve donde el medio categoriza en la URL.** Los de Nintendo no lo
  hacen: GoNintendo cuelga todo de `/contents/` y Nintendo Life de `/news/`.
  Ahi el trabajo lo sigue haciendo `tema`, y por eso los dos filtros conviven.
- **Se comprueba igual que `tema`, midiendo**: agrupar por el primer tramo de
  la URL lo ya publicado de ese medio y mirar que caeria. Si cae una sola
  noticia buena, la ruta sobra.
- Es preferible a pedir el feed de la categoria buena, que fue lo primero que
  se penso: ni Hipertextual ni ADSLZone declaran mas feed que el general en su
  portada, y adivinar la ruta del feed por categoria es justo lo que este
  proyecto ya aprendio a no hacer.

En la misma medicion se ampliaron seis formulas de `RUIDO`, tambien sacadas de
lo que se colo de verdad y no de lo que suena a ruido: `", analisis:"` en medio
del titular, "hunde/tumba/desploma el precio", "ahorrate", "consiguelo",
"por solo N" y "sorteo/regalamos". Dos candidatas se cayeron al medirlas, y por
eso no estan: **"rebaja"** a secas tiraba "Digi rebaja el roaming en cuatro
paises", que es noticia de telecos, y **"por menos de N"** tiraba "Xiaomi lanza
una lavadora un 30% mas eficiente por menos de 450 euros", que es un
lanzamiento. Las seis que quedaron no tocan ninguna de las 1.211.

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

### Y un "no" que no es tecnico: mirar el robots.txt

Al valorar ocho medios el 14-08-2026, tres venian con la nota de que bloqueaban
a los scripts (El Chapuzas "402", TechPowerUp "deteccion de bots", Nintendo
World Report "su robots.txt prohibe el acceso automatico"). **Los tres
descargaron a la primera**, o sea que las tres notas eran falsas. El robots.txt
de Nintendo World Report son 34 bytes con un `Crawl-delay` para msnbot: no
prohibe nada.

Pero **TechPowerUp si prohibe**, y ese es el motivo por el que se quedo fuera.
Ahora bien, hay que leer **cual** de los dos "no" es, porque son distintos y
confundirlos deja una regla que este proyecto se salta en 8 sitios.

**El "no" por nombre no nos aplica.** Casi todos los medios grandes llevan
bloques del tipo `User-agent: ClaudeBot` -> `Disallow: /`. Eso le habla a un
rastreador concreto, el que Anthropic pasea por la web por su cuenta. Nuestro
script no es ese: se lanza cuando lo lanza la rutina y **pide el RSS**, que es
un fichero que el medio publica justamente para que lo lean programas y lo citen
con enlace. Prueba de que no va con nosotros: ninguno de ellos cierra el feed.
Quien no quiere que le lean cierra de verdad, como Nintendo Wire, que da 403
hasta en la portada.

Si ese bloque contase como veto, habria que echar a **TechCrunch, The Verge,
Areajugones, Nintendo Everything, The Register, 404 Media y Nintenduo**: son
8 de los 26 medios activos, medido el 15-08-2026. O sea, media seccion de
tecnologia por una regla que nadie estaba aplicando.

**El "no" general si nos aplica.** El de TechPowerUp no nombra rastreadores:
dice que esta prohibido *"any device, tool, or process designed to data mine or
scrape the content using automated means... without prior written permission"*.
Eso no habla de IA, habla de **cualquiera que automatice**, y `candidatos` es
exactamente eso. Su punto (1), el "text and data mining" del Art. 4 de la
Directiva europea, es la clausula que permite a un medio reservarse ese derecho,
y ese robots.txt es la reserva. **El Chapuzas** esta en la misma zona por
`ai-train=no`.

Ojo con citar el punto (2) de TechPowerUp ("the development of any software,
machine learning, AI and/or LLMs") como motivo: habla de **desarrollar o
entrenar** modelos, que es justo lo que aqui no se hace. El (4), "commercial
purposes", tampoco, porque la web no monetiza.

Asi que el criterio, en una linea: **veta la prohibicion general de automatizar,
no el bloqueo por nombre de rastreador.** Y el feed respondiendo no es permiso,
igual que en Amazon: ahi el limite tampoco era tecnico.

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

## La seccion de IA

Abierta el **21-08-2026**, sacandola de tecnologia. La idea de partida era otra
—dividir tecnologia en IA y hardware— y lo que la cambio fue medir las 680
noticias de tecnologia ya publicadas y la materia prima de 48 h de sus feeds:

| | Publicado | Materia prima | Por turno |
|---|---|---|---|
| IA | 26% | 14% | 9,5 |
| Hardware | 13% | 11% | 7,2 |
| Ni una ni otra | **59%** | **74%** | 49,5 |

Los dos motivos por los que la division en dos no se hizo estan en esa tabla:

- **Partir en IA y hardware no reparte, amputa.** Casi tres cuartas partes de
  lo que hay no es ni una cosa ni la otra: espacio, ciberseguridad, telecos,
  redes sociales, software, juicios, centros de datos. Sin una seccion que las
  recoja se pierden, y con ella la division no es tal, son dos secciones nuevas.
- **Hardware no da de comer.** 7,2 candidatos por turno contra los 30 que pide
  el formato (5 destacadas + 25 titulares). Saldria medio vacia dos veces al
  dia, que es peor que no tenerla.

IA si da, pero **no con los feeds de tecnologia** (9,5 por turno). Da con feeds
de categoria, que es lo que se busco despues: simulando la seccion entera salen
**18 candidatos por turno de 10 medios, 3 de ellos espanoles**. De ahi que la
lista de `ia` en `medios.json` no sea la de tecnologia con un filtro: la mitad
son feeds de la seccion de IA del medio (TechCrunch, The Verge, Ars, y el de
Hipertextual, cuya ruta con `/categoria/` delante da 410).

Tres cosas que hay que saber para no romperla:

- **Los cupos de esta seccion son mas bajos** (15 titulares de tope, 8 minimos
  por la manana), y viven en `CUPOS` dentro de `noticias.py`. Una seccion
  estrecha no es una seccion mal hecha: pedirle los 25 de tecnologia solo
  conseguiria que `validar` avisara en todas las ejecuciones. Ahi esta tambien
  la unica regla que cambia de rango: **no traer ninguna destacada de un medio
  espanol es aviso y no error**, porque los medios espanoles de IA dan 2
  candidatos por turno y habra turnos sin ninguno. Un ERROR que quien lo recibe
  no puede corregir solo ensena a saltarse los errores.
- **Tecnologia ya no publica IA**, y por eso su bloque `tema_ajeno` en
  `medios.json` apunta a la lista de `ia`. Se apunta, no se copia: dos listas
  iguales en dos sitios acaban distintas, y el dia que se desincronizan aparece
  una noticia que no entra en ninguna de las dos. Tecnologia se queda con 84
  candidatos por turno de los que 13 se van a IA, o sea que no se resiente.
- **La lista `propio` de IA son nombres propios y siglas**, no conceptos. Esta
  a proposito **sin "Nvidia"** (vende tarjetas graficas de juego), sin "chip" y
  sin "algoritmo": el filtro se aplico a las 680 publicadas y las 196 que se
  llevaba eran todas de IA, sin un solo falso positivo. Con "Nvidia" dentro,
  una noticia de graficas para jugar acabaria en la seccion de IA.

Como el filtro decide **de que va la noticia y no de quien viene**, se aplica a
todos los medios de tecnologia y no solo a los generalistas, al reves que
`filtrar_tema`. Un medio dedicado solo a IA no se pone en tecnologia.

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

**El job lleva `timeout-minutes` porque un fallo mudo ya paso.** El 19-08-2026
el paso de instalar Playwright se quedo colgado y el job estuvo **seis horas**
ahi hasta que GitHub lo mato por su limite; la pasada de la manana se perdio.
Lo peor no fue perderla sino que **un run cancelado no avisa**: el fallo solo
se vio al revisar el historial dos dias despues. Con el tope, un cuelgue acaba
en fallo, y un fallo si manda correo. La ejecucion normal tarda 3-4 minutos, o
sea que 20 no aprieta nada.

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

**Amazon esta con `solo_enlace`, y la distincion importa.** Lo que prohibe su
normativa es **sacarle el precio con un script**, no que se enlace a una ficha
suya: un hipervinculo no le pide nada que no le pida cualquier web que la cite.
Asi que desde el 14-08-2026 esta en el catalogo como El Corte Ingles y Fnac,
con su enlace y sin consultarla nunca.

Lo que **no** hay que hacer es ascenderla a tienda con precio. Sus fichas
responden perfectamente a `urllib` (las siete devolvieron 200 y su titulo al
comprobarlas), asi que la tentacion va a estar ahi: **que se pueda no quiere
decir que se deba**, y aqui el limite no es tecnico. Es el unico sitio del
catalogo donde `solo_enlace` no significa "no responde" sino "no se le pide".

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

**La cadencia son dos pasadas al dia** (14-08-2026; antes era una), a las 6:10
y las 14:10 hora espanola, que es cuando las tiendas han movido ya la tanda de
la manana y la del mediodia. **El techo no es el coste sino parecer una visita
normal**: el runner es gratis (repo publico, minutos ilimitados) y aqui no
interviene Claude, asi que la tentacion de subir la frecuencia no la frena
ningun contador. La frena que consultar cada media hora deja de ser una visita,
y lo que se juega es la seccion entera: quien empieza a bloquear no devuelve
precios peores, devuelve 403.

La segunda pasada **si aporta**, y eso hubo que medirlo porque se metio dando
por hecho lo contrario: aqui puso que los precios de videojuegos "no se mueven
dentro del mismo dia". Revisadas las 12 ejecuciones del 15 al 21-08-2026,
**4 de las 6 pasadas de tarde trajeron cambios** (entre 1 y 3 precios), y no
son de redondeo: Carrefour subio Star Fox de 50,99 a 54,99 una tarde y
MediaMarkt bajo Elliot de 66,99 a 61,90 en otra. Sin la pasada de tarde la web
habria dado esos precios con medio dia de retraso. Lo que sigue en pie es el
techo por arriba: dos pasadas se quedan, tres no se prueban.

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

**Y ese 502 tampoco era aleatorio: era pedir la ficha en frio.** Al meter los
cuatro juegos de Switch 1, tres de sus fichas de Xtralife daban 502 sin fallar
una sola vez en 18 intentos, mientras Star Fox y Octopath II entraban siempre.
Parecia que esas fichas estuvieran rotas, y no: **con la sesion recien creada
dan 502, y tras cargar cualquier otra pagina suya dan 200**, medido dos veces
seguidas con cada opcion. Las fichas mas visitadas responden bien igual, que es
lo que hacia parecer el fallo cosa de la tienda y no del modo de pedir.

Lo que **no** se puede hacer es visitar la portada siempre, y esto es lo que
tiene gracia: **PcComponentes y Carrefour dan 403 si la sesion viene de su
portada, o si se les piden dos fichas seguidas con la misma sesion.** Medido el
mismo dia: sesion compartida y calentada, 12 fichas de 14 caidas; sesion nueva
y en frio, ninguna. Lo que cura a una tienda mata a las otras dos.

Por eso `Navegador._contexto()` crea **una sesion nueva para cada ficha** y solo
recuerda a que dominios hay que calentarles la portada, aprendido del primer
fallo (`self._calentar`). Quien va bien en frio no paga nada; Xtralife pierde el
primer intento de su primera ficha y a partir de ahi entra a la primera. Si
calentando tampoco sale, el dominio se olvida, para no arrastrar toda la
ejecucion una receta que no funciona.

La leccion que se repite: **antes de dar una tienda por rota, cambiar como se
pide**. Primero fue el 403 (script contra navegador), ahora el 502 (en frio
contra con sesion). En los dos casos la ficha estaba perfectamente.

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

- **Cada producto es un `<details>` plegado**: se ve el nombre y el precio mas
  bajo, y las tiendas salen al pulsar. Con el catalogo creciendo, la lista
  desplegada obligaba a hacer scroll para comparar dos juegos entre si, que es
  lo primero que se mira. Es `<details>` nativo y no un desplegable a mano
  porque trae gratis el teclado, el estado para los lectores de pantalla y la
  busqueda del navegador dentro de la pagina.
- **El precio de la cabecera es el mas bajo de hoy**, y solo si ninguna tienda
  ha respondido se cae al mas bajo que se conserve, diciendolo con un "no es de
  hoy" al lado. Es la misma regla que impide a un `viejo` competir por "Mas
  barato", aplicada al sitio mas visible de la pagina: ahi un precio de hace
  dias sin avisar se leeria como el precio de hoy.

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
