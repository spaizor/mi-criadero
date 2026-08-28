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
geopolitica.html      seccion (carga data/geopolitica.json)
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

Ese indice recien creado lleva **`"desde"`**, el primer turno que se le va a
pedir. Sin eso, `estado` reclama los turnos de los dias anteriores a que la
seccion existiera, y un aviso que sale siempre y no significa nada es un aviso
que se deja de leer. Admite dia (`"2026-08-22"`) o **dia y turno**
(`"2026-08-21_T"`), que es lo que hace falta de verdad: una rutina nueva
empieza a la hora que se crea, no a medianoche. `ia` arranco una tarde, y con
la fecha a secas habia que elegir entre reclamar una manana que nunca existio o
no vigilar su primer turno. Si la rutina se crea mas tarde de lo previsto, hay
que mover ese valor.

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
python3 scripts/noticias.py indexar    <seccion>   rehace el indice del buscador
python3 scripts/noticias.py comprobar              secciones dadas de alta enteras
python3 scripts/noticias.py publicar   "<mensaje>" commit de data/ y push
python3 scripts/noticias.py estado                 que turnos faltan por publicar
python3 scripts/noticias.py vigilar                las tres comprobaciones, desde la rutina
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
2. El modelo escribe `data/<seccion>.json` con **las 7 destacadas y los
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

#### Medir lo publicado no basta: `adslzone.net/noticias/streaming-tv/`

**Esta ruta se probo el 22-08-2026 y se dejo fuera, asi que no hay que volver a
meterla sin releer esto.** Parecia el caso de libro: 18 titulares publicados,
todos estrenos de cine, series y futbol por TV ("SkyShowtime estrena el viernes
la nueva pelicula...", "Hoy tienes futbol gratis en la TDT"), ni uno de la
seccion. Mas volumen incluso que el `/cine-television/` de Hipertextual.

Lo que lo tumbo fue mirar **el feed y no solo lo publicado**, y ahi esta la
leccion que sirve para la proxima ruta: lo publicado es lo que el modelo ya
eligio, o sea una muestra sesgada de la categoria. Ese mismo dia el feed traia
por esa ruta **"Ya es oficial: YouTube Premium sube otra vez de precio en
Espana"**, que es noticia de tecnologia de pleno derecho. Un solo falso positivo
y la ruta sobra, que es la regla de arriba.

El motivo de fondo es que la categoria del medio **mezcla dos cosas**: los
estrenos (ruido) y el negocio de las plataformas (noticia). Donde si se separan
solas es en `/noticias/operadores/`, por donde han entrado las buenas de este
tipo (Movistar Plus, la comparativa de precios del futbol).

Ese corte mas fino se hizo el **27-08-2026**, y es `excluir_en_ruta`, mas
abajo. La ruta sigue sin excluirse entera, que era lo correcto.

En la misma medicion se ampliaron seis formulas de `RUIDO`, tambien sacadas de
lo que se colo de verdad y no de lo que suena a ruido: `", analisis:"` en medio
del titular, "hunde/tumba/desploma el precio", "ahorrate", "consiguelo",
"por solo N" y "sorteo/regalamos". Dos candidatas se cayeron al medirlas, y por
eso no estan: **"rebaja"** a secas tiraba "Digi rebaja el roaming en cuatro
paises", que es noticia de telecos, y **"por menos de N"** tiraba "Xiaomi lanza
una lavadora un 30% mas eficiente por menos de 450 euros", que es un
lanzamiento. Las seis que quedaron no tocan ninguna de las 1.211.

### `excluir_en_ruta`: cuando la categoria mezcla dos cosas

`excluir_rutas` tira una categoria entera y por eso **no puede equivocarse**:
no adivina de que va la noticia, lee donde la colgo el medio. El problema es la
categoria que mezcla, y de esas hay una: `adslzone.net/noticias/streaming-tv/`
cuelga los estrenos de las plataformas (ruido) junto al negocio de esas mismas
plataformas (noticia). Por eso el 22-08-2026 no se pudo excluir, ver arriba.

`excluir_en_ruta` es un campo del medio en `medios.json` que empareja una ruta
con una lista de terminos: **dentro de esa ruta**, el titular que mencione uno
se descarta. Es lo mismo que `tema` pero al reves y acotado, y se aplica en los
dos comandos que leen feeds.

**La medicion, hecha el 27-08-2026 sobre la portada de la categoria y no sobre
lo publicado**, que era justamente el error de la primera vez: de sus 57
entradas (unos cinco dias), **54 eran estrenos y programacion** y **3 eran
noticia de tecnologia** ("YouTube Premium sube otra vez de precio en Espana",
"Se acaba el chollo de compartir YouTube Premium", "Los nuevos Fire TV de
Amazon volveran a permitir instalar aplicaciones externas"). La lista de 32
terminos caza **34 de los 37 ruidos** de los que se tenia el titular entero y
**ninguna de las 3 buenas**. Los 3 que escapan no dicen ninguna palabra del
oficio ("Antoni Daimiel se despide de Movistar Plus").

**Lo que hay que tener claro es que esta lista no se puede sacar de su ruta**, y
esto tambien esta medido: aplicada a las otras rutas de ADSLZone se llevaba
**16 de 104 publicadas**, entre ellas "Movistar, Orange o DAZN: compara cuanto
pagaras por ver todo el futbol" y "Digi tendra la tele con menos futbol de toda
Espana", que son noticias de telecos de pleno derecho. Dentro de
`/streaming-tv/` "futbol" es programacion; en `/operadores/` es el negocio. El
mismo termino cambia de significado con la categoria, que es exactamente por lo
que el filtro va atado a una y no al medio.

Por eso el orden al atacar un ruido nuevo es: **primero `excluir_rutas`**, que
no puede fallar, y solo si la categoria mezcla, esto. Un filtro por titular
siempre puede equivocarse; lo unico que lo hace aceptable aqui es que solo mira
dentro de una categoria donde ya se sabe que significan las palabras.

**Lo que sigue entrando**, y no es un descuido: el ruido de cine y series que
ADSLZone cuelga en `/noticias/operadores/` ("Movistar Plus estrena el domingo
una pelicula de accion"). Ahi la misma lista se lleva las noticias de telecos,
asi que hoy no hay corte que valga. Tambien publica de supermercados (Lidl,
Mercadona), que es otro asunto y esta sin medir.

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

### El buscador del historico

Con 1.211 noticias guardadas, el desplegable de dia y turno ya no bastaba:
encontrar algo obligaba a abrir turno por turno. Desde el 21-08-2026 `archivar`
mantiene ademas un indice en `data/historico/<seccion>/busqueda/AAAA-MM.json`
con el titulo, la fuente, la fecha, el enlace y el turno de cada noticia, y
`historico.html` filtra sobre el.

**Un fichero por mes y no uno solo con los 90 dias, y esto se midio.** El indice
crece a 24 KB al dia entre las tres secciones. Con un fichero unico, cada turno
reescribe los 90 dias enteros: **1,5 GB al ano** de churn en el repo. Por meses
solo se reescribe el mes en curso y baja a **0,2 GB**, y ademas un mes cerrado
no se vuelve a tocar nunca. Los meses que hay que pedir salen del `indice.json`,
que ya se descarga.

Cuatro cosas mas que hay que saber:

- **Se rehace el mes entero en vez de anadir al final.** Leer sus turnos cuesta
  milisegundos y asi el fichero se repara solo si un dia sale mal. Por eso mismo
  **no lleva marca de tiempo dentro**: sin ella, rehacerlo sin cambios deja el
  fichero identico y git no ve un cambio donde no lo hay.
- **El indice se descarga al escribir la primera letra, no al abrir la pagina.**
  Quien entra a mirar el turno de ayer no tiene por que pagar 240 KB; quien
  busca acepta esperar una vez, y despues se queda en memoria.
- **Se busca solo en la seccion abierta**, la que dicen las pestanas. Con las
  tres a la vez habria que bajarse los tres indices para la primera letra que se
  teclee. Cuando no hay resultados, el aviso lo dice y manda a probar en otra.
- **Se descartan las repetidas por enlace**, quedandose con el turno mas
  reciente: el buscador esta para encontrar una noticia, no para contar cuantas
  veces se publico. En nintendo eso junto 531 en 529.

`indexar` rehace todos los meses de una seccion. Sirve para sembrar una seccion
anterior al buscador (asi se hizo con tecnologia y nintendo) o para reparar; el
dia a dia lo lleva `archivar` solo.

**Los tres limites del historico no son el mismo, y conviene tenerlo claro:**
en disco no caduca nada (las rutinas no borran); el desplegable de dia y turno
enseña los ultimos 90 dias exactos (`DIAS` en `historico.html`); y el buscador
cubre esos mismos 90 dias **redondeados al mes**, porque los meses salen de las
entradas ya filtradas pero se pide el fichero del mes entero. Si el corte cae el
23 de mayo, `2026-05.json` entra completo. En la practica el buscador ve entre
90 y 120 dias segun el dia del mes. No se noto hasta ahora porque el historico
empezo el 07-08-2026: los tres limites coinciden hasta el 05-11-2026.

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
fuera. Y `candidatos` no cubre las destacadas, que siguen exigiendo abrir y
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

Cada seccion tiene dos niveles: **7 destacadas** que la rutina abre y lee (6
en `ia`, ver mas abajo), y
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
  el formato (7 destacadas + 25 titulares). Saldria medio vacia dos veces al
  dia, que es peor que no tenerla.

IA si da, pero **no con los feeds de tecnologia** (9,5 por turno). Da con feeds
de categoria, que es lo que se busco despues: simulando la seccion entera salen
**18 candidatos por turno de 10 medios, 3 de ellos espanoles**. De ahi que la
lista de `ia` en `medios.json` no sea la de tecnologia con un filtro: la mitad
son feeds de la seccion de IA del medio (TechCrunch, The Verge, Ars, y el de
Hipertextual, cuya ruta con `/categoria/` delante da 410).

Tres cosas que hay que saber para no romperla:

- **Los cupos de esta seccion son mas bajos** (6 destacadas en vez de 7, 15
  titulares de tope, 8 minimos por la manana), y viven en `CUPOS` dentro de
  `noticias.py`. Una seccion
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
- **El titular no basta para separarlas, tambien se mira de que feed vienen.**
  Los dos primeros turnos con IA abierta publicaron una noticia repetida en las
  dos secciones cada uno, las dos de TechCrunch: "Nvidia partners with data
  center developer Cloverleaf" y "Starcloud raises $250 million for orbital data
  centers". Ninguna decia en el titular una palabra de `propio` ("Nvidia" esta
  fuera a proposito y "data center" no esta), asi que `tema_ajeno` no podia
  cazarlas. Pero el propio medio ya las habia clasificado: estaban en su feed de
  IA. `enlaces_de_la_hermana()` descarta lo que el medio cuelga en el feed de la
  seccion hermana, que es `de_otra_seccion` aplicado a las hermanas: alli la
  categoria se lee en la URL y aqui en de que feed viene. Medido el 22-08-2026:
  de 8 noticias en los dos feeds a la vez, el titular cazaba 6 y escapaban esas
  2. Solo cuesta descargas en los medios con feed aparte para la hermana
  (Hipertextual, TechCrunch, The Verge y Ars Technica), y si ese feed no
  responde no se descarta nada suyo y se avisa: quedarse sin un medio entero por
  un fallo de red es peor que la repetida que esto evita.
- **La lista `propio` de IA son nombres propios y siglas**, no conceptos. Esta
  a proposito **sin "Nvidia"** (vende tarjetas graficas de juego), sin "chip" y
  sin "algoritmo": el filtro se aplico a las 680 publicadas y las 196 que se
  llevaba eran todas de IA, sin un solo falso positivo. Con "Nvidia" dentro,
  una noticia de graficas para jugar acabaria en la seccion de IA.

Como el filtro decide **de que va la noticia y no de quien viene**, se aplica a
todos los medios de tecnologia y no solo a los generalistas, al reves que
`filtrar_tema`. Un medio dedicado solo a IA no se pone en tecnologia.

## La seccion de Geopolitica

Abierta el **28-08-2026**. Medios de fuera del bloque occidental: rusos, chinos,
turcos, iranies, asiaticos y latinoamericanos, mas la prensa occidental no
alineada. Es la seccion **mas ancha del proyecto**: 32 medios vivos y **236
candidatos por turno**, contra los 84 de tecnologia y los 18 de `ia`. Por eso
lleva **8 destacadas**, una mas que nintendo: aqui el numero lo permite lo que
hay, al reves que en `ia`, donde se bajo a 6 porque no daba.

### Sale una vez al dia, y por eso `secciones.json` declara los turnos

Su rutina corre solo por la manana, a las **5:30**. Eso rompia algo que no se veia:
`estado` exigia siempre M y T a toda seccion con historico, asi que cada noche a
partir de las 21:00 habria dado el turno de tarde de geopolitica por perdido. Y no
es un mensaje en un log: `vigilancia.yml` habria mandado un correo todos los dias y
`noticias.py vigilar` habria dejado la banda roja fija en la portada. El aviso que
sale siempre acaba tapando a los que significan algo.

Por eso cada seccion declara en `assets/secciones.json` los **`turnos`** que
publica (`["M", "T"]` o `["M"]`), que es lo que `estado` exige. Va ahi y no en el
script porque es lo mismo que ya decide el resto del alta, y `comprobar` avisa si
una seccion con historico no lo declara. Los cupos por turno (`MIN_TITULARES`,
`min_medios`) siguen en `noticias.py` y no cambian: la seccion usa los de `M`.

Al pasar a un solo turno, la ventana de `candidatos` pasa a ser de 24 h en vez de
12, asi que trae mas material, no menos.

### No lleva filtro de tema, y menos aun filtro geografico

Lo primero que se penso fue acotarla a **lo que afecta a Europa y a Espana**. Se
midio sobre los 944 titulares de 48 h antes de escribir nada, y no sale:

| Que se exige | Brutos por turno | Historias **distintas** por turno |
|---|---|---|
| Europa + Espana | 23,5 | **16,8** |
| + Ucrania | 31,2 | — |
| + Ucrania + Rusia | 44,5 | **33,8** |
| Solo Espana | 2,8 | — |

Con 8 destacadas y 25 titulares hacen falta **33**. O sea que el filtro estricto
deja la seccion **a la mitad**, mas estrecha que `ia`, que ya va justa; y metiendo
Rusia y Ucrania da el cupo exacto y sin margen, ademas de convertirla en la guerra
de Ucrania narrada por TASS y RT, que es otra seccion distinta de la que se queria.

**Hay que contar historias y no titulares**, y esto es lo propio de esta seccion:
32 medios cubren las mismas noticias del dia. La muerte del rey Harald V de Noruega
salio en **12 de los 21 medios** que pasaban el filtro. El pipeline descarta
repetidos por enlace y por titulo **dentro de un mismo medio**, no la misma noticia
contada por diez, asi que cuanto mas se aprieta el filtro mas se nota.

Y la lista de terminos falla como ya avisa este fichero, con el agravante de que los
nombres de pais salen en cualquier noticia: `Haya` caza *"Cancilleria descarta que
**haya** mexicanos afectados"*; `Europa` caza *"BJK face tough **Europa** League
draw"* y no se puede quitar del filtro de Europa; `Berlin` caza *"2 dead in school
attack near Berlin"*. Sucesos, futbol y cultura.

**Asi que no se filtra, se prioriza:** los 25 titulares son geopolitica mundial sin
filtro, y las **8 destacadas las elige el modelo entre lo que toca a Europa y a
Espana**, que es criterio editorial y no se deja escribir como lista. Hay 16,8
historias europeas distintas por turno, o sea margen 2 a 1 para llenar 8.

### Los medios: se eligen, no se filtran

En nintendo el ruido lo quita `tema`; aqui lo quita **no dar de alta al medio**. Los
generalistas nacionales se quedan fuera aunque traigan mucho: Yonhap da 101 entradas
cada 48 h de liga de beisbol, estrenos e incendios, y ademas publica la misma noticia
4 y 5 veces con prefijos `(LEAD)`, `(2nd LD)` y `(URGENT)`, que el descarte por
titulo no caza. Lo mismo Korea Herald, The Straits Times y Nhan Dan. Los que entran
son los que traen geopolitica de oficio.

`excluir_rutas` se usa donde el medio categoriza en la URL, medido el 28-08-2026:
TASS (`/sports/`, `/science/`), Daily Sabah (`/sports/` son 11 de sus 50 entradas, y
`/arts/` 4) y The Hindu (`/sport/`, `/videos/`). En TRT World, CGTN, Africanews y
Sputnik no se puede: cuelgan todo de una ruta unica y **sus feeds de seccion no
existen**, se probaron y dan 404.

**`min_medios` sube a 8 por la manana** en vez de los 5 de las demas. El tope de 5
titulares por medio ya reparte, pero con 32 medios cubriendo las mismas cinco
noticias del dia la seccion se puede llenar con TASS, RT y tres mas y quedar contada
por un solo bloque. Exigir 8 es gratis teniendo 32 vivos.

### `descartado`: el aviso que salia siempre

Los 11 medios sondeados y dejados fuera se quedan en `medios.json` para no volver a
probarlos, pero llevan **`"descartado": true`** y por eso no salen como `SIN FEED` en
el parte de `candidatos`. `SIN FEED` es para el medio al que todavia hay que buscarle
el RSS o abrir a mano, o sea una tarea; una decision ya tomada repetida en las dos
ejecuciones de todos los dias es un aviso que sale siempre y se deja de leer.

Ahi esta tambien por que se cayo cada uno, y tres son de los que este proyecto ya
sabe distinguir: **Xinhua no bloquea**, su certificado lo firma la CA china CFCA, que
no esta en el almacen de Python, y solo entraria desactivando la verificacion.
**Press TV** tiene la cadena incompleta y ademas su feed no trae ni una fecha, igual
que China Daily y Hankyoreh. **RT y Sputnik** no fallan por su culpa: la sancion de
la UE los deja fuera desde Espana, y se entra por los espejos `www.rt.com` y
`noticiaslatam.lat`. Las rutas buenas de teleSUR, TRT World y Nhan Dan salieron
**leyendo la portada**, que es lo que manda este fichero: las adivinadas daban 404.

### TRT World publicaba los enlaces relativos

Su feed da `/article/e12d692b1e86` en las 100 entradas, no la URL entera, y asi
llegaba al JSON: un enlace roto en la web. Lo caza `validar`, pero para entonces
la noticia ya esta escrita y hay que rehacerla. Desde el 28-08-2026
`entradas_del_feed` acepta la portada del medio como base y resuelve el enlace con
`urljoin`, que no toca los que ya son absolutos. Es el unico medio de los 32 que lo
hace, pero el arreglo va en el sitio comun porque el siguiente feed que lo haga
entraria igual de callado.

### Lo que queda pendiente: el ruido de los medios en espanol

Los `idioma: es` **no pasan por el modelo**, se publican tal cual sale del feed. Son
5 (Sputnik Mundo, teleSUR, Resumen Latinoamericano, Prensa Latina, Anadolu Espanol),
dan 29 candidatos por turno y cubren de sobra la destacada espanola que exige
`validar`. Pero en la primera pasada colaron *"Carlos Alcaraz debutara ante Roman
Safiullin en el US Open"* y *"Pelicula dominicana La Bachata de Bionico llegara a
cines de Mexico"*: aproximadamente uno de cada cuatro.

**Y aqui no hay filtro que no pueda fallar**: ninguno de los cinco categoriza en la
URL (Sputnik y teleSUR meten el titular entero, Anadolu cuelga todo de `/es/`, y los
otros dos van en la raiz), asi que `excluir_rutas` no sirve. Lo unico que hay es el
`<category>` del propio feed, que **si declaran teleSUR, Resumen Latinoamericano y
Prensa Latina**, y no declaran Sputnik ni Anadolu. Seria un mecanismo nuevo, y este
proyecto no mete un filtro con la muestra de un dia: se decide con el historico de
los primeros dias, igual que se hizo con `excluir_rutas`.


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

**Y al reves: una bajada que parece un fallo y no lo es.** El 24-08-2026 los
cinco juegos que se siguen en MediaMarkt bajaron a la vez exactamente un 17,36%,
que es justo dividir por 1,21. Cinco productos con la misma caida al centimo es
un error de IVA de libro... salvo que no lo era: la tienda estaba de promocion
"sin IVA" y el precio publicado era el bueno.

Como se distingue, y hay que mirarlo **antes** de tocar nada: la ficha lo dice.
Su bloque `Offer` trae un `priceSpecification` con un `StrikethroughPrice`, que
es el precio anterior (50,90 en un Star Fox a 42,07), y el precio nuevo repetido
como "Standard price" para socios y para no socios. Si lo que leemos aparece
como precio vigente y lo viejo como tachado, es una rebaja de verdad.

La leccion es la de siempre aqui, pero aplicada al reves: **medir antes de dar
algo por roto**, no solo antes de darlo por bueno. La coincidencia aritmetica
convencia sola, y bastaron treinta segundos de volcar el bloque de la ficha para
ver que quien se equivocaba era el diagnostico.

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

### El precio objetivo, la serie y los avisos

Anadido el 23-08-2026. Tres piezas que responden a la misma pregunta: cuando
comprar.

**El objetivo** es un campo opcional de `productos.json` (`"objetivo": 30`). La
web pinta **siempre lo que falta** (`Tu precio: 30,00 EUR - te faltan 20,90`), no
solo cuando se cruza, y eso se decidio midiendo: los siete objetivos piden
caidas de entre el 25% y el 53%, y en quince dias de datos **ninguno se habia
rozado**. Una marca que apareciera solo al cumplirse no se veria en meses; la
distancia dice algo cada dia. Al cruzarse, entonces si, pastilla grande.

Los objetivos **se publican** en `data/ofertas.json`, y el repositorio es
publico. No es un dato sensible, pero conviene saberlo antes de ponerlos.

**La serie** vive en `data/precios/AAAA-MM.json`, con un punto **solo cuando un
precio cambia**. Tambien medido: de las 889 lecturas guardadas en los 39 commits
que habia, solo **62 traian un precio distinto, el 7%**. Una entrada por pasada
guardaria catorce veces el mismo numero. Al ser escalonada -un precio vale hasta
el punto siguiente- no se pierde nada. Por meses, por lo mismo que el indice del
buscador.

`precios.py sembrar` la reconstruye desde el historial de git, que es donde ya
estaba: cada commit de la seccion es una pasada. Asi el grafico nacio con quince
dias dentro en vez de vacio. Con `--rehacer` reescribe tambien los meses que ya
tengan fichero.

**El grafico dibuja una sola linea: el precio mas bajo del producto en cada
momento**, no una por tienda. Seis lineas en 44 px no se leen, y la pregunta a
la que se viene es cuanto ha costado el juego. Dos detalles que costaron:

- **Los puntos del mismo instante entran todos antes de calcular el minimo.**
  Uno a uno, la primera pasada dibujaba un escalon que nunca existio: Super
  Mario RPG arrancaba en 56,12 y caia a 39,99 en el mismo minuto, solo porque en
  el primer evento aun no se conocian las demas tiendas. Lo caza una simulacion
  de la serie, no la vista.
- **El objetivo solo se dibuja en el grafico si cae dentro de lo que ha valido.**
  Con un objetivo un 40% por debajo, meterlo en la escala aplastaria la linea
  contra el techo y no se veria ningun movimiento.

**Los avisos de la portada** salen en dos casos y solo en dos: un juego que llega
a su objetivo, y **una bajada en Orange**, donde hay ventajas por comprar. El
resto de bajadas se ven dentro de la seccion con su etiqueta; subirlas todas a
la portada la llenaria de avisos a diario y se dejarian de leer.

**Ojo con las bajadas de Orange**, que es justo la tienda donde el aviso es mas
fragil: su precio no se lee, se reconstruye de una cuota mensual, y **el plazo
no esta en la ficha sino a mano en el catalogo**. Si Orange cambia la
financiacion de 24 a 36 meses, el precio reconstruido caeria un tercio sin que
el PVP se mueva, y eso llegaria a la portada como una bajada. Ante una bajada
suya sospechosamente redonda, lo primero que hay que mirar es el plazo.

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

## Vigilancia: los fallos que no avisaban

Dos agujeros del mismo tipo, tapados el 23-08-2026 con la misma idea que ya
habia arreglado el cuelgue de Playwright: **convertir un fallo mudo en uno
ruidoso**.

### `.github/workflows/vigilancia.yml`

Las rutinas de noticias **no corren en GitHub** sino en la nube de Anthropic, asi
que si fallan aqui no se entera nadie: no hay job que falle ni correo que salga.
Lo unico que se ve es que ese dia falta un turno en `data/historico/`, y para
verlo hay que acordarse de mirar.

El workflow lanza `estado --dias 2 --local` a las **09:15 y 21:15**, y como
`estado` sale con codigo 1 cuando falta un turno, el job falla y **GitHub manda
el correo solo al dueno del repositorio**. La direccion no se publica en ninguna
parte; lo que si es publico, como en cualquier repo publico, es el log del run,
que dice que turnos han salido y a que hora.

Tres decisiones:

- **Las horas son las de `LIMITE_TURNO`** (9:00 y 21:00). Antes de esa hora un
  turno que falta esta pendiente, no perdido: las rutinas salen a las 4:00 y
  16:30 y hay margen para un reintento. Avisar antes seria una falsa alarma cada
  manana.
- **`--local` y no la comparacion contra `origin/main`.** El checkout que se
  acaba de hacer ES `origin/main`, asi que traerlo otra vez solo anade una
  llamada de red que puede fallar y dar una falsa alarma.
- **`timeout-minutes`, con mas motivo que en precios**: un job colgado no avisa,
  y este existe justamente para avisar.

Lo que **no** arregla: un turno perdido no se recupera, porque los feeds solo dan
lo reciente. Lo que se gana es enterarse el mismo dia para mirar el log en
https://claude.ai/code/routines antes del turno siguiente, en vez de descubrirlo
dos dias despues.

### `precios.py frescura`: el cron que no dispara

Anadido el **27-08-2026**, y por un caso real. `precios.yml` ya falla cuando
ninguna tienda responde, pero eso solo cubre **las veces que llega a
ejecutarse**: ese dia GitHub no lanzo su cron de las 6:10 y la seccion se quedo
con los precios de la tarde anterior sin que hubiera un job en rojo ni un
correo. **Un cron que no dispara no falla**, que es el mismo tipo de agujero que
ya taparon `estado` y el `timeout-minutes` de Playwright.

`frescura` mira el `actualizado` de `data/ofertas.json` y sale con codigo 1 si
falta la pasada que ya tocaba. Lo lanza `vigilancia.yml` detras de `comprobar`,
con `if: always()`, y tambien `noticias.py vigilar`.

#### Medir la antiguedad no valia: el 28-08-2026 el fallo tapaba al vigilante

**La primera version comparaba la antiguedad de la ultima pasada contra un tope
de 12 horas, y hay que entender por que no servia, porque suena equivalente.**
La antiguedad se mide contra la pasada anterior, no contra la hora a la que
tenia que haber salido esta. Ese dia GitHub se salto el cron de las 6:10, pero
**la pasada anterior habia llegado con diez horas de retraso, a las 00:12**: a
las 9:15 el vigilante veia 9 horas, por debajo del tope, y daba verde con la
seccion sin actualizar.

O sea que **cuanto mas se retrasa GitHub, mas reciente parece la pasada que se
ha perdido**. El mismo fallo que hay que cazar desactivaba al que lo caza, y el
razonamiento de las 12 horas ("si una se salta, se veran 19") daba por hecho que
la anterior habia llegado a su hora, que es justo lo que aqui no pasa nunca.

Ahora se compara contra un **horario fijo**: `pasada_exigible()` calcula la
ultima hora de `HORAS_PASADA_UTC` que ya vencio, y se exige una pasada posterior
a ella. A las 9:15 se pide una posterior a las 6:10 y da igual cuando llego la
de ayer.

- **Las horas van en UTC, que es lo que ponen los cron**, no en las 6:10 y 14:10
  espanolas de su comentario. Solo se nota medio ano y ahi lo rompe: en invierno
  el cron cae a las 5:10 espanolas, asi que exigir una pasada posterior a las
  6:10 daria AVISO todas las mananas con los precios recien traidos. Salio
  simulando enero, **despues de haber escrito en el codigo que llegar antes de
  la hora exigida "nunca da falsa alarma"**, que es exactamente al reves.
- **`MARGEN_PASADA` son 2 horas de retraso perdonadas**, y el numero esta
  medido, no elegido: sobre los 31 runs programados del 10 al 27-08-2026, la
  mediana de retraso son 36 min por la manana y 56 por la tarde, con 62 de
  maximo en regimen normal. Con 2 horas ni el peor dia normal avisa, y el fallo
  se sigue cazando el mismo dia.
- **El mismo calculo hace de guardia en `precios.yml`**, con `--margen 0`: ahi
  la pregunta pasa de "hay que avisar de que falta" a "hay que hacerla". Que sea
  la misma funcion es lo que impide que las dos ideas de "pasada pendiente" se
  separen con el tiempo.

**Lo que no cubre, y no es un descuido:** que se salte el cron del propio
vigilante, que es justo lo que paso ese dia. Dos workflows del mismo
repositorio se retrasan por el mismo motivo, asi que esto caza la averia
frecuente (precios falla, la vigilancia corre) y no la simultanea. Taparla
entera pide vigilar desde fuera de GitHub.

**Y a diferencia de un turno de noticias, la pasada perdida si se recupera**:
los feeds solo dan lo reciente, pero la ficha de la tienda sigue teniendo el
precio de hoy. Por eso el error manda a lanzar `Precios` a mano desde Actions,
para lo que ya estaba el `workflow_dispatch`.

### Los cron de repesca: GitHub no dispara a su hora nunca

Al medir el 28-08-2026 los 31 runs programados de `precios.yml` desde el 10-08
salio algo que no se sabia: **ni uno solo ha disparado a su hora**. El retraso
va de 33 a 62 minutos en regimen normal (mediana 36 por la manana, 56 por la
tarde), y a partir del 26-08 por la tarde salta a 174, 178, 500, 602 y 661
minutos, con dos pasadas saltadas enteras.

**El retraso no es cola de runner**, y eso descarta la explicacion facil: en los
31 runs, `run_started_at - created_at` es **0,0 minutos siempre**. Lo que llega
tarde es la creacion del run, o sea el planificador de cron de GitHub. No se
arregla con mas maquina ni con un runner propio, porque el problema ocurre antes
de que haya runner.

Los 40 minutos de mas dan igual: un precio que entra a las 6:50 vale lo mismo.
Lo que no da igual es la pasada que no sale, asi que la salida es **pedirla mas
veces**: cada tramo tiene su cron principal y **dos repescas** (a +1h30 y +3h30).
Si la primera no dispara, dispara la siguiente.

- **No publican tres veces al dia** porque el paso `guardia` del workflow lanza
  `frescura --margen 0` antes de nada: si la pasada del tramo ya esta hecha, el
  job acaba en segundos sin instalar Playwright ni abrir Chromium. En un dia
  normal las dos repescas son eso, segundos de runner gratis.
- **Van despues, no antes.** Adelantar el cron para compensar el retraso medio
  seria adivinar; una repesca no pierde nada si la buena ya salio.
- **Lo que no arreglan** es el dia en que GitHub deja de disparar cron durante
  horas, como el 27-08: ahi caen las tres. Esa es la averia que tiene que cazar
  `noticias.py vigilar`, que corre fuera de GitHub, y por eso los dos arreglos
  van juntos.

### `noticias.py vigilar`: el vigilante que no vive en GitHub

El 27-08-2026 no dispararon **ni el cron de precios ni el de `vigilancia.yml`**.
O sea que el agujero que se acababa de tapar seguia abierto por debajo: el
vigilante que avisa de los fallos de GitHub **vive en GitHub**, y cuando lo que
falla es el planificador, callan los dos a la vez. No es mala suerte: dos
workflows del mismo repositorio se retrasan por el mismo motivo.

`vigilar` es esa misma comprobacion desde otra infraestructura. Lo lanza una
**rutina de Claude**, que corre en la nube de Anthropic: hace `estado`,
`comprobar` y `frescura`, y si algo falla escribe `data/vigilancia.json` y lo
publica. La portada lo pinta como una banda de aviso, que es donde se mira
todos los dias sin tener que acordarse.

Cuatro decisiones:

- **Todo el trabajo esta en el script, no en el prompt.** Es la regla de este
  proyecto llevada al extremo: el prompt de la rutina es una linea, el modelo
  no decide nada y la ejecucion cuesta segundos. Una rutina que solo mira si
  algo va mal no puede costar como una que escribe noticias.
- **Solo se escribe el fichero cuando cambia lo que dice.** En un dia normal no
  hay avisos y no hay commit; el dia que se arregla, se escribe una vez la
  lista vacia y la banda desaparece sola. Un commit diario que solo mueve una
  marca de tiempo es ruido, igual que en la serie de precios.
- **Una vez al dia, por la manana** (9:30, despues del `LIMITE_TURNO` de la
  manana). Es el minimo que caza un fallo el mismo dia; la segunda pasada la
  sigue haciendo el workflow, que para eso es gratis.
- **El aviso va delante de los de precio y con color de alerta**, no con el
  verde de ofertas: no habla de un precio, dice que lo que hay debajo puede no
  ser de hoy. Leerlo despues no serviria de nada.

Lo que **no** arregla: si un dia falla la rutina en si, nadie avisa. Se podria
seguir encadenando vigilantes para siempre; a partir de aqui lo razonable es
que dos infraestructuras distintas no callen el mismo dia.

#### Y desde el 28-08-2026 no avisa de los precios: los lanza

La pasada de precios perdida **se recupera entera**, al reves que un turno de
noticias: los feeds solo dan lo reciente, pero la ficha de la tienda sigue
teniendo el precio de hoy. Estando eso a un clic, avisar y esperar a que alguien
lea el aviso era conformarse con menos de lo que se puede hacer.

La pieza que lo permite es que **`workflow_dispatch` no pasa por el planificador
de cron**, que es lo unico que se rompe: es una llamada a la API que se atiende
al momento. Por eso el consejo de "lanzalo a mano desde Actions" funciona justo
los dias en que el cron no dispara. `lanzar_pasada()` en `precios.py` hace esa
llamada, y `vigilar` la usa cuando `frescura` falla.

- **Lo que viaja es el pistoletazo, no el trabajo.** `consultar` necesita
  Chromium para cuatro de las seis tiendas, o sea instalar un navegador en cada
  ejecucion de una rutina cuyo unico cometido es mirar si algo va mal. El runner
  de GitHub ya lo tiene montado y es gratis: lo que falla ahi es cuando empieza,
  no lo que hace.
- **Si el lanzamiento sale bien, el aviso no llega a la portada.** El problema se
  esta corrigiendo solo y la banda seguiria puesta el resto del dia. Y no deja un
  agujero mudo, que es lo que habria que temer: si el run recien lanzado falla,
  es un job en rojo y GitHub manda el correo. La banda se pinta solo cuando **no**
  se consigue lanzar (sin token, sin red, permiso caducado), que es cuando de
  verdad hace falta una persona.
- **Sin token no se rompe nada**: se devuelve el motivo y se avisa como antes. Un
  vigilante que se cae por no poder arreglar el problema es peor que uno que solo
  avisa.
- **El token va en la variable de entorno `GITHUB_TOKEN_PRECIOS`**, nunca en el
  repositorio (es publico) ni en `data/`. Necesita permiso de escritura en
  Actions y nada mas. `python3 scripts/precios.py lanzar` sirve para probarlo a
  mano; con `--siempre` dispara aunque la pasada del tramo ya este hecha.

**Ojo: hoy ese camino no lo usa la rutina, y no es un olvido.** Se monto para
que lo usara y al configurarlo se vio que **una rutina de Claude no admite
variables de entorno ni secretos**: su `job_config` solo lleva el entorno, el
prompt, el modelo, las fuentes y las herramientas. La unica forma de colarle el
token seria escribirlo en el prompt, y eso **no se hace**: cada comando queda en
el transcript de cada ejecucion, o sea que el token acabaria en texto plano en
el log de todas las ejecuciones para siempre. El codigo se queda porque sirve
para lanzarla a mano desde un PC con el token en el entorno, y por si algun dia
las rutinas admiten secretos.

Asi que quien da el pistoletazo es el `on: push` de `precios.yml`, abajo.

#### El disparador de verdad: el push de la propia vigilancia

`vigilar` ya escribe y publica `data/vigilancia.json` cuando falta la pasada, y
ese push sale **desde la nube de Anthropic, ajena al planificador de cron de
GitHub**, que es lo unico que se rompe. O sea que el pistoletazo ya estaba ahi
sin darse cuenta: solo faltaba que `precios.yml` lo escuchara.

- **Dispara solo con `data/vigilancia.json`.** Es el unico fichero que cambia
  cuando algo va mal, asi que el disparo ocurre justo en el caso que interesa y
  no en los seis push diarios de las rutinas de noticias.
- **No puede realimentarse.** Este workflow publica `data/ofertas.json`, que no
  esta en `paths`; y ademas GitHub no relanza workflows por un push hecho con el
  `GITHUB_TOKEN` del runner.
- **El guardia decide igual que con los cron**, asi que un push que llegue con
  la pasada ya hecha acaba en segundos. Solo `workflow_dispatch` se salta el
  guardia, porque si lo lanzas a mano es que quieres que consulte.
- **Lo que cuesta**: por esta via la banda de aviso **si** aparece en la portada
  y se queda hasta la vigilancia del dia siguiente, aunque los precios se hayan
  arreglado dos minutos despues. Con el token no pasaria, porque entonces el
  aviso no llega a escribirse. Es el precio de no guardar una credencial.

**Lo que faltaba por comprobar el 28-08-2026**, y se ve a la primera cuando
ocurra: si el push de una rutina dispara workflows depende de con que credencial
empuje, y no habia ningun workflow `on: push` en el repositorio con el que
haberlo visto antes. Si no dispara, en el historial de Actions no saldra el run
de Precios detras del commit de vigilancia, y entonces la via es otra.

Lo que **no** cubre: si GitHub Actions esta caido del todo, el dispatch tampoco
entra. Pero eso ya no es un fallo mudo, porque la llamada devuelve el error y
entonces si se pinta la banda.

### `assets/secciones.json` y el comando `comprobar`

Dar de alta una seccion toca **ocho sitios** (su HTML, el chip y la entrada de
`index.html`, tres reglas de `estilo.css`, `medios.json` y el `indice.json` con
su `desde`), y el problema no es que sean muchos: es que **olvidarse de uno no
rompe nada de forma visible**. Sin su bloque en el historico la seccion funciona
pero no tiene dias anteriores; sin el `desde`, `estado` reclama turnos de antes
de que existiera. Los dos aparecen semanas despues.

`secciones.json` es ahora la lista buena. **La leen** `historico.html` (las
pestanas), `scripts/iconos.py` (los cuatro colores, en ese orden) y `comprobar`.
**No la leen, y no es un descuido:**

- **`estilo.css`**, porque una hoja de estilos no puede leer un JSON. Los
  `--acento-<acento>` siguen a mano, y `comprobar` vigila que no falte ninguno.
- **`index.html`**, porque sus chips y entradas escritos son lo que hace que la
  portada se quede como estaba cuando un fetch falla, en vez de en blanco.
  Generarlos ahorraria repetirlos y cambiaria robustez por menos duplicacion, y
  en la pagina que mas se abre ese cambio no compensa. En `historico.html` si se
  depende del fetch porque sin red esa pagina no tiene nada que ensenar de todas
  formas.

`comprobar` cruza la lista con el repo en los dos sentidos: avisa de la seccion
que este a medias, y tambien de los medios o las carpetas de historico de una
seccion que ya no esta en la lista. Probado dando de alta una seccion falsa: los
ocho sitios que faltaban salieron como ocho errores, cada uno diciendo que hacer.
El workflow lo lanza detras de `estado` con `if: always()`, para que un alta a
medias se vea en el mismo correo y no en el de doce horas despues.

**Al anadir la quinta seccion hay que decidir que hace el icono**: son cuatro
cuadros en rejilla, asi que `iconos.py` se planta a proposito si la lista no
tiene cuatro. Quedarse con las cuatro primeras dejaria una seccion fuera sin
decirlo.

## Icono, manifest y previsualizacion

La web se lee en el movil todos los dias, asi que desde el 21-08-2026 se
instala como una app: `manifest.json` en la raiz, iconos en `assets/` y las
metas en el `<head>` de las seis paginas.

**El icono lo genera `scripts/iconos.py`, no un editor de imagenes.** Los cuatro
colores salen de `assets/estilo.css` (`--acento-tec`, `--acento-ia`,
`--acento-nin`, `--acento-ofe`), asi que el dia que cambie el acento de una
seccion se regenera con `python3 scripts/iconos.py` en vez de repintarlo a
mano. Escribe el PNG a mano con `zlib` y `struct`, que para figuras planas son
treinta lineas, y asi el script sigue la regla del proyecto de no depender de
nada que no sea la biblioteca estandar.

El dibujo son los cuatro colores en rejilla, **sin letras a proposito**: a 32 px
una inicial no se lee, y cuatro manchas de color si se reconocen entre veinte
pestanas.

Cuatro cosas que hay que saber para no romperlo:

- **El "maskable" lleva mas margen que los demas** (26% contra 14%). Android
  recorta ese icono a un circulo y solo garantiza el 80% central: con el margen
  normal le cortaria las esquinas a los cuadros de arriba.
- **El de Apple va cuadrado y opaco.** iOS redondea el icono el solo y no lleva
  bien la transparencia: se la rellena de negro.
- **`og:image` y `og:url` van en absoluto.** Quien genera la previsualizacion de
  WhatsApp o Telegram no resuelve rutas relativas; con una relativa la imagen
  simplemente no sale. Por eso son las unicas URL del proyecto que llevan el
  dominio escrito.
- **No se ponen las metas de standalone de iOS** (`apple-mobile-web-app-capable`)
  y no es un olvido: alli capturan la navegacion, y esta web enlaza todo el rato
  a medios de fuera, que se abririan dentro sin barra ni boton de volver. En
  Android el `display: standalone` del manifest si se pone, porque los enlaces
  externos salen en una pestana del sistema que si tiene con que volver.

Nada de esto lo tocan las rutinas: `publicar` hace `git add` solo de `data/`.

## Publicacion

GitHub Pages esta configurado como *Deploy from a branch* → `main` → `/ (root)`.
Cualquier push a `main` republica la web, pero **tarda 1-2 minutos**. Si un
cambio no se ve al instante, esperar antes de darlo por fallido.
