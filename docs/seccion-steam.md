# La seccion de Steam

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

Abierta el **18-09-2026**. Hermana de Ofertas y con la misma regla: no busca
rebajas, sigue una lista cerrada que vive en `scripts/juegos-steam.json`. Lo
que cambia es de donde sale el precio, y ese cambio lo simplifica todo.

```
python3 scripts/steam.py consultar         escribe data/steam.json
python3 scripts/steam.py probar <appid>    una ficha suelta, sin publicar
python3 scripts/steam.py probar-ig <id>    una ficha de Instant Gaming
python3 scripts/steam.py descubrir         rellena nombre, id y ediciones
python3 scripts/steam.py frescura          ha salido la pasada de hoy?
```

La actualiza `.github/workflows/steam.yml`, no una rutina de Claude: aqui no
se elige nada, igual que en Ofertas.

## gg.deals no era el camino, y el motivo no es el de siempre

Era la fuente de partida. Esta **cerrada de verdad**, y hay que saber
distinguirlo del 403 de MediaMarkt, que este fichero ya explica:

| Peticion | Resultado |
|---|---|
| Ficha con User-Agent de Chrome | 403 |
| Ficha con curl pelado | 403 |
| **Portada** | **403** |

El cuerpo del 403 es `<title>Just a moment...</title>` con CSP de
`challenges.cloudflare.com`: es un desafio de Cloudflare. **403 en la portada
ya no es el modo de pedir**, que es justo el corte que separa a MediaMarkt (se
cura con navegador) de Nintendo Wire y El Corte Ingles (no se curan). Y
saltarse un challenge no es cambiar el User-Agent: es evadir una deteccion, o
sea el lado equivocado del limite que este proyecto ya se puso con Amazon.

Su `robots.txt` lista ademas `ClaudeBot` en un bloque "AI training". Por el
criterio de este fichero eso seria bloqueo por nombre y no vetaria nada, pero
da igual: el muro tecnico es anterior.

## La API de Steam, medida

Sin clave, sin registro y sin navegador:

| | |
|---|---|
| Latencia | **0,20 s** |
| **30 appids en una peticion** | 0,35 s, 3.954 bytes, los 30 devueltos |
| 10 peticiones seguidas | 200 en todas, sin estrangulamiento |
| `robots.txt` | `Disallow` de `/share/`, `/email/`, `/widget/` y rutas de cuenta. **`/api/` no esta**, y no hay prohibicion general de automatizar |
| La pasada entera (50 juegos + 17 ediciones) | **13 s** |

Devuelve `initial`, `final` y `discount_percent` en centimos, o sea que **el
precio de referencia y el descuento vienen de serie**, que es el dato que
Ofertas no tiene y que aqui es media seccion.

Por eso `steam.py` **no necesita Playwright** y cumple el "solo biblioteca
estandar" que si rompe `precios.py`. Su workflow no instala nada.

**El lote va atado a `filters=price_overview`.** Con ese filtro la API admite
varios appids; con `basic` admite uno y con varios devuelve `null`. No es una
limitacion que se pueda quitar subiendo el numero.

**Y Steam comprime sin que se lo pidan**, ignorando un `Accept-Encoding:
identity`: su respuesta a `basic` con lista llega en gzip sin anunciarlo. Es
el caso de Vandal otra vez, asi que `pedir()` mira el numero magico `1f 8b`
igual que `noticias.py`. Ojo con esto al tocar `precios.py`: **su `descargar()`
NO descomprime**, y hoy no molesta solo porque sus tiendas no comprimen.

### `cc=es` no es cosmetico

Sin `cc`, Steam responde en la moneda de la IP que pregunta, y el runner de
GitHub puede estar en cualquier region. Los numeros serian perfectamente
validos y perfectamente falsos, que es el fallo mudo de siempre. Por eso
`de_precio()` **comprueba que vuelve en EUR** y aborta si no: es la unica forma
de cazarlo.

## El catalogo se congela, y por eso no hay SteamID en el repositorio

Salio de la lista de deseados del usuario, leida **una sola vez** con
`IWishlistService/GetWishlist` (publico, sin clave). Podria leerse en cada
pasada, y **no se hace a proposito**: eso obligaria a escribir su SteamID en
un repositorio publico. Congelada, lo unico que se publica es que juegos
sigue, que es lo mismo que ya publica Ofertas.

Para refrescarla hay que volver a dar el perfil a mano. El endpoint de la
**biblioteca** (`GetOwnedGames`) si pide clave; la lista de deseados no.

## Las ediciones especiales salen de la ficha, no de una busqueda

Fue la duda al montarla: encontrarlas automaticamente o escribirlas a mano.
Automaticamente, y sin buscar nada: **estan en `package_groups` de la propia
ficha del juego**, o sea en sus opciones de compra. `storesearch` era el camino
equivocado, porque devuelve los DLC mezclados y todos con `type: app`.

De ahi cuelgan tres cosas que no son ediciones, y las tres se descartan:

- **El juego base**, a veces repetido con el nombre en ingles (Sackboy,
  DRAGON QUEST XI S). La regla que lo caza no es comparar nombres: **si un
  juego tiene una sola opcion de compra, esa opcion ES el base**, se llame como
  se llame.
- **`Commercial License`**: la licencia para negocios (UNCHARTED y los dos
  Spider-Man). Gana al termino de edicion, porque "Legacy of Thieves
  Collection - Commercial License" lleva las dos cosas.
- **`DLC Pack`** y `All In One DLC Pack` (Persona 3 Reload, Persona 5
  Tactica), que es justo lo que no se queria.

Y **se exige un termino de edicion en vez de descartar lo que suene mal**, que
es lo mismo que decidio el bloque `tema` de `medios.json` y por el mismo
motivo. Medido sobre las 74 opciones de compra de los 50 juegos: **17
ediciones, ni un falso positivo ni un falso negativo.**

**Se compara sin tildes en los dos lados**, y esto no es teorico: sin eso se
perdia la "Edicion Super Limit-Breaking NEO" de DRAGON BALL, que era el unico
falso negativo de la medicion. Las demas "Edicion X" entraban por otra palabra
("deluxe", "completa"), asi que el fallo estaba tapado por suerte de la
muestra.

### Los bundles son un tercer tipo de producto, y hay ediciones que solo existen asi

**Esto se dio por inexistente el 18-09-2026 y era falso**, asi que conviene
tenerlo claro: mirar `package_groups` y `storesearch` **no agota el catalogo de
Steam**. Hay un tercer sitio, los *bundles*, que no sale en ninguno de los dos.

Se vio porque el usuario contesto que "Cyberpunk 2077: Ultimate Edition" y
"WORLD OF FINAL FANTASY COMPLETE EDITION" si existian, y tenia razon: son los
bundles **32470** y **9112**. La ficha de Cyberpunk solo vende el juego a
59,99, y la busqueda de la tienda no devuelve ninguno de los dos. El unico
sitio donde estan es el **HTML de la ficha**, en un enlace `/bundle/<id>/`.

Es otra vez la leccion del feed de 3DJuegos: **se lee, no se adivina**, y aqui
ademas ensena algo nuevo, que es que una API oficial y completa puede seguir
dejandose cosas fuera.

Se resuelven con `actions/ajaxresolvebundles`, y ahi hay una trampa:

- **`final_price` viene a CERO** en los dos bundles comprobados, con el precio
  de verdad solo en `formatted_final_price` ("82,78€"). Tiene la forma del
  campo bueno y no lo es. Se lee del formateado y se comprueba contra la
  cuenta, que cuadra al centimo: `initial_price` 8998 x (1 - 8%) = 8278.
- **`initial_price` es la suma de las partes sueltas**, que es justo lo que
  Steam tacha al lado del precio del pack, asi que sirve de `base`.
- El descuento que se publica es el **efectivo**, que sale de juntar
  `bundle_base_discount` (el fijo por comprar el pack) y `discount_percent`
  (el promocional, casi siempre 0).

**`descubrir` NO los mete solo, y esta medido.** De los 44 bundles que enlazan
los 50 juegos del catalogo, la mayoria **no son ediciones del juego**: son
packs de dos juegos distintos ("Mina the Hollower + Mewgenics"), colecciones de
genero ("Metroidvania Souls-Like Bundle") o sagas enteras ("Trine: Ultimate
Collection", que son cinco juegos; "Blasphemous Franchise Collection"). La
lista de terminos de arriba coleria varias de esas, porque dicen "Ultimate" y
"Collection" siendo otra cosa. Asi que **los bundles se anaden a mano** y
`probar <appid>` los ensena con su precio para poder copiarlos, con
`"bundleid"` en el sitio del `"packageid"`.

### El corte por indice pide otra funcion que la comparacion

`acortar()` quita el nombre del juego del de la edicion, y ahi **la
normalizacion de compatibilidad no vale**: descompone el simbolo de marca
registrada en dos letras, asi que cortar por la longitud del texto normalizado
desplaza el corte. "Edicion Completa de Stellar Blade(tm)" salia como "Edicion
Complet". Por eso `plano()` conserva la longitud y solo quita tildes. Para
comparar sirve cualquier version; para cortar, no.

En ingles el juego va delante ("ELDEN RING Shadow of the Erdtree Edition") y
en espanol detras ("Edicion Completa de Stellar Blade"), asi que hay que mirar
por los dos lados o la mitad de los nombres salen duplicados.

**Y hay que igualar los espacios**, que fue el segundo caracter invisible que
rompio lo mismo: el nombre de "Guardianes de la Noche" lleva un **espacio duro**
(U+00A0) donde su propia opcion de compra lleva uno normal, asi que la edicion
salia sin acortar, con el nombre del juego repetido entero delante. `plano()`
cambia cualquier separador de espacio por el normal, uno a uno y no con una
expresion, para no romper la promesa de conservar la longitud.

## "Sin precio" son dos cosas distintas

Y la ficha las distingue sola con `release_date.coming_soon`, asi que no hay
nada que adivinar:

- **`proximamente`**: anunciado pero sin fecha ni precio (Super Yooka-Laylee
  Kart).
- **`retirado`**: ya salio y Steam ya no lo vende. A Horizon Zero Dawn Complete
  Edition le paso al salir la Remastered: conserva sus `packages` pero no tiene
  precio.

Publicarlos como un "sin precio" comun perderia la diferencia, que es la misma
idea que el `disponible: null` de GAME: no declarar el stock no es estar
agotado. Y **ninguno de los dos es un fallo de la consulta**, asi que su
etiqueta no puede leerse como una averia.

## Las ediciones no compiten, y eso cambia la vista

Es la diferencia de fondo con Ofertas y la unica parte de `ofertas.js` que no
se reutiliza. Alli las filas son tiendas y **compiten**: la pregunta es donde
esta mas barato, y por eso hay un "Mas barato" y un "+9,00 EUR" contra el.
Aqui las filas son ediciones del mismo juego y **no compiten**: la Deluxe no es
la estandar mas cara, es otro producto con mas cosas dentro. Coronar la
estandar como la mas barata seria dar por hecha una comparacion que no
significa nada.

Lo demas si se reutiliza: `steam.html` carga `assets/ofertas.js` antes que
`assets/steam.js` y de ahi salen el formateo de precios y todo el dibujo del
grafico. **No se copian** porque dos copias de la misma funcion acaban siendo
dos funciones distintas, que es lo mismo que evita que `tema_ajeno` de
tecnologia apunte a la lista de IA en vez de repetirla. Cargar `ofertas.js` no
ejecuta nada por si solo: su `cargarOfertas()` la llama el HTML de Ofertas.

Tres decisiones mas de la vista:

- **Los rebajados van primero.** Con 50 juegos, lo que se viene a ver es que ha
  bajado hoy, y en orden alfabetico eso obliga a recorrer la lista entera.
- **El grafico dibuja solo la edicion estandar.** Mezclarlas daria una linea
  que salta de un producto a otro cada vez que sale una edicion nueva, y la
  pregunta es cuanto ha costado EL juego.
- **La fila es un grid de tres columnas heredado de Ofertas**, asi que el
  precio tachado y el de hoy van envueltos en un solo elemento. Sueltos serian
  un cuarto hijo y se irian a la linea de abajo; se vio en la primera captura.

## Los precios objetivo

Los paso el usuario el **18-09-2026**, el mismo dia. Son **51** sobre 52
juegos: 43 en el juego (se aplican a su edicion estandar) y **8 en una edicion
concreta** (Shadow of the Erdtree, la Deluxe de Digimon, la Complete de FINAL
FANTASY XVI, la Beyond the Dawn de Tales of ARISE, la Legendaria de DRAGON
BALL, la Ultimate de Guardianes de la Noche y los dos bundles de Cyberpunk y
WORLD OF FINAL FANTASY).

Tres juegos entraron con ellos, **aunque no estuvieran en la lista de
deseados**: Horizon Zero Dawn remasterizado (que sustituye a la *Complete
Edition*, retirada de la venta) y los dos Guardianes de la Noche.

**Por eso el `objetivo` va por edicion y no por juego**, al reves que en
Ofertas: una Deluxe a 22 EUR y un juego base a 22 EUR son metas distintas, y
esos cuatro juegos no tienen objetivo para su version normal. En el catalogo se
puede escribir en los dos sitios; el del juego lo hereda su estandar.

La web pinta **siempre lo que falta** (`te faltan 6,99 EUR`) y no solo al
cruzarse, por lo mismo que en Ofertas y con la misma medicion detras: el dia
que se pusieron **no habia ni un objetivo cumplido**, y al mas cercano (NEEDY
GIRL OVERDOSE) le faltaba 1,51 EUR. Una marca que apareciera solo al cumplirse
no se veria en meses.

En la cabecera del bloque va **solo el objetivo de la estandar**, que es el
precio que se ve plegado. Los de las ediciones se leen al abrir, al lado del
precio con el que hay que compararlos: subirlos arriba pondria dos metas
distintas junto a un solo numero.

Los objetivos **se publican** en `data/steam.json` y el repositorio es publico,
igual que los de Ofertas.

## El titulo enlaza a Steam, y el catalogo lleva la URL escrita

El catalogo guarda `enlace` en cada juego aunque salga del `appid`: sirve para
abrir la ficha con un clic mientras se edita el fichero, que es donde se
trabaja al anadir un juego. **No es una segunda fuente de verdad** porque no lo
lee nadie: el script arma la URL del `appid` igual que antes, y `descubrir` lo
reescribe. Si los dos no cuadran, manda el `appid`.

En la web el nombre del juego es el hipervinculo. Vive dentro del `<summary>`,
asi que sin pararle la propagacion al clic abriria la ficha **y** plegaria el
bloque a la vez. Se delega en el contenedor y no se pone en cada enlace: son 52
juegos y el HTML se reescribe entero en cada carga.

## Los avisos de la portada, y por que ahora si

Cuando se monto la seccion no los llevaba: sin objetivos, lo unico que se podia
avisar era una rebaja, y ese dia habia **18 juegos rebajados de 50**. Un aviso
por rebaja llena la portada a diario y se deja de leer.

Con los objetivos puestos ya hay algo que merece subir, y sale **solo eso**: un
juego, o una edicion suya, que llega a su precio. Las rebajas normales siguen
dentro de la seccion con su etiqueta. Que no vaya a salir casi nunca es la
condicion para que se lea el dia que salga, y esta medido: cero cumplidos de 43.

**`pintarAvisos` recibe la lista y ya no el JSON de una seccion.** Antes hacia
`innerHTML =` con los avisos de Ofertas, y como la portada carga las entradas en
paralelo, la segunda seccion en llegar habria borrado los avisos de la primera.
Ahora cada una empuja los suyos y se pintan juntos al final; cada aviso lleva su
`destino` porque enlazan a paginas distintas.

La entrada de la portada **ya no resume la mejor rebaja**: desde el 22-09-2026
dice cual esta mas cerca de su precio objetivo, por lo que se explica en la
seccion de Ofertas. Lo que sigue en pie es que la cuenta de rebajados de la
derecha mira **solo las ediciones estandar**: una Deluxe al -70% sigue costando
mas que la normal, y coronarla seria vender como chollo el producto caro.

## Vigilancia: el mismo camino que precios

`steam.py frescura` es el mismo mecanismo que el de `precios.py`, horario fijo
en UTC incluido y por los mismos motivos (medir la antiguedad no vale, y las
horas en local rompen medio ano). Lo lanzan `vigilancia.yml` y
`noticias.py vigilar`.

En `vigilar` las dos van por el mismo camino porque **las dos se recuperan
enteras**: la ficha de la tienda y la API de Steam siguen teniendo el precio de
hoy, al reves que un turno de noticias. Y las dos las dispara el push de
`data/vigilancia.json`, que ya esta en el `paths` de `steam.yml`. Por eso el
bloque de precios de `vigilar` se generalizo en `pendiente()` en vez de
duplicarlo.

**Steam no lleva el lanzador con token y no es un olvido**: ese camino no lo usa
nadie hoy, porque una rutina de Claude no admite secretos. Lo que la lanza de
verdad es el push.

**Y su import va dentro de un `try`, al reves que el de `precios`.** No es
desconfianza del fichero: es que `vigilar` lo lanza una rutina de Claude y es
**el unico vigilante que vive fuera de GitHub**. Si un fallo al cargar
`steam.py` lo tumbara entero, se quedarian sin vigilar tambien los turnos, las
secciones y los precios, o sea justo la averia para la que se monto. Cuando no
carga, lo dice y sigue con lo demas. Probado rompiendo el fichero a proposito.

## Las demas tiendas, via ITAD

Anadido el **19-09-2026**, y cambia la pregunta de la seccion: de "cuanto cuesta
en Steam" a **"donde lo compro"**. Merece la pena porque esta medido: **30 de
los 50 juegos con precio estan mas baratos fuera de Steam**, y no por centimos
(Persona 5 Tactica 59,99 -> 16,19; Blasphemous 24,99 -> 5,44).

Lo trae `scripts/itad.py`, solo biblioteca estandar. **Una peticion por pasada**
para los 52 juegos (el endpoint admite 200), asi que la pasada pasa de 13 a 16
segundos y no instala nada; el limite de ITAD son 1.000 peticiones cada 5
minutos. El `appid -> id de ITAD` se resuelve una vez con `descubrir` y se
congela en el catalogo, igual que la lista de deseados.

**La clave va en el secret `ITAD_API_KEY` y viaja en la cabecera
`ITAD-API-Key`, no en la URL.** ITAD admite las dos formas y la de la URL es la
peligrosa: el log de Actions de un repositorio publico lo ve cualquiera, y basta
una traza que imprima la direccion para dejar la clave escrita ahi para siempre.

### Por que ITAD y no abrir las tiendas

Es la leccion de `precios.py` aplicada **antes** de cometer el error. Abrir la
ficha de cada tienda son 52 juegos por N tiendas con Chromium de por medio, o
sea justo el coste que esta seccion no paga.

Y las tiendas de keys grises estan **cerradas de verdad**: G2A, Kinguin, Gamivo
y CDKeys responden 403 con un reto de Cloudflare **en la portada**, que es el
corte que ya fijo gg.deals. Da igual: **ITAD no sigue ninguna de las seis**. De
sus 34 tiendas para Espana, todas son autorizadas o revendedores legitimos, asi
que la pregunta del mercado gris se contesta sola. La unica alcanzable a mano
seria Instant Gaming, y pedirla exigiria Playwright para una sola tienda.

### Los tres filtros, todos medidos

**1. Fuera las que no cotizan en euros.** No se ven en la moneda, porque ITAD
convierte y entrega todo como EUR: se ven en el numero.

- Por el **ratio contra Steam**: WinGameStore y GamesPlanet US dan 0,871
  constante (el dolar) en 25 y 23 juegos con desviacion 0,015, y GamesPlanet UK
  0,976 (la libra). Las demas dan exactamente 1,000.
- Por los **centimos de la tarifa**, que caza a las que convierten con margen
  variable y el ratio no ve: una tienda en euros pone precios de escaparate y
  acaba en .99, .95 o .49 casi siempre. Muve da un 62% de tarifas redondas,
  Zapagames un 0% (25,03 / 30,04) y Fortuna Digital un 0% (26,13, que son
  exactamente 29,99 USD x 0,871).

Cuesta un 9% del ahorro y a cambio **no hay un solo precio "estimado"** en la
seccion. Solo ELDEN RING pierde su mejor precio, por diez centimos.
GamesPlanet esta fuera entera ademas por decision del usuario: no tiene tienda
espanola. **Esta lista se repasa con la cuenta de los centimos cuando ITAD de de
alta una tienda nueva**, y se queda escrita a mano en vez de automatizar la
regla: una lista no puede equivocarse, y un filtro por centimos tiraria en
silencio una oferta buena el dia que una tienda ponga un precio raro de verdad.

**2. Fuera GOG, DRM-Free y Microsoft Store**, que son copias que no se van a
usar: su precio no es mas barato, es otra cosa. Cuesta un 12% (de 34 juegos mas
baratos fuera se pasa a 29) y ningun juego se queda sin ofertas.

**La regla que sostiene ese filtro es que lo que NO declara plataforma se
conserva.** De las 51 ofertas sin `drm`, **50 son de la propia Steam**, que no
declara lo obvio: descartar lo no declarado la tiraria entera. Y es tambien lo
unico que deja entrar a Ubisoft, porque **"Uplay" y "Ubisoft Connect" no existen
como valor en la API**: buscarlos por nombre no habria encontrado ni una.

**3. Fuera la propia Steam**, aunque ITAD la traiga: su precio ya esta en
`ediciones` y mas fresco. Dos numeros para lo mismo en el mismo fichero no se
pueden arbitrar el dia que discrepen.

### El deduplicado es por tienda MAS plataforma

Parece que basta con quedarse con el mas barato de cada tienda, y no: Fanatical
vende el Devil May Cry de **Steam a 8,69** y el de **GOG a 25,49**, y DLGamer el
Persona 5 Tactica de Steam a 18,00 y el de Microsoft Store a 59,99. **Son
productos distintos, no dos precios del mismo**, y juntarlos haria parecer que
hay una comparacion donde no la hay. Repetidos de verdad los hay -SteamWorld
Heist II sale dos veces en Fanatical al mismo precio- y esos si se funden.

### Los cupones se publican con su codigo

Son 36 ofertas. **El precio que da ITAD ya los lleva aplicados**, comprobado:
`regular x (1 - cut)` da el precio al centimo. Asi que el cupon no se resta, se
**dice**: son codigos que reparte la propia tienda (`FANATICAL15`,
`HOLA15ITAD`), y sin decirlo el precio parece sencillamente mal.

### Si ITAD falla, la pasada publica igual

Sin clave, sin red o con `itad.py` roto, `consultar` publica los precios de
Steam y lo dice en el parte. Es la regla de `enlaces_de_la_hermana()`: quedarse
sin seccion por un fallo de algo accesorio es peor que publicar sin el
accesorio. Probado rompiendo las tres cosas a proposito.

### La vista: dos ejes que no se mezclan

Las **ediciones** no compiten (son productos distintos) y las **tiendas** si
(es el mismo juego en sitios distintos), asi que van en dos listas separadas por
una linea, y solo las de abajo llevan "Mas barato" y "+X,XX". Sin esa linea se
leen como una sola lista donde unas filas compiten y otras no, que parece un
fallo.

La cabecera dice el **precio mas bajo de hoy y donde** ("en GreenManGaming 5,44
EUR"), y el objetivo se compara contra ese: si ha llegado a tu precio en
Fanatical, ha llegado. La lista se ordena por **el mayor descuento en cualquier
sitio**: mirando solo el de Steam, un juego al -70% en Fanatical y a 0% en Steam
se iba al fondo, que es justo el que se viene a ver.

Tres cosas que se decidieron viendolo pintado y no antes:

- **"Aqui se vio a X" se quito.** Salia en 191 de las 252 filas, y con las
  marcas de ITAD encima eran **las 252, o sea todas**. No es que fuera falso:
  ITAD guarda anos de historial y la mediana de esas rebajas pasadas es del
  **58%**, asi que cualquier tienda ha tenido cualquier juego mucho mas barato
  alguna vez. Es lo mismo que ya decidio `ofertas.js`, donde salia en 18 de 24.
  Queda solo la **marca de ITAD** (`H` minimo historico, `N` nuevo minimo, `S`
  minimo de esa tienda), que sale en el 24% y dice que el precio de HOY lo es.
- **Cuanto ha llegado a costar el juego se dice una vez**, en la cabecera del
  bloque y no por fila, porque es una pregunta del juego. Sale de `minimo_itad`
  y se dice **"en cualquier tienda"** a proposito: cubre tambien las que aqui no
  se publican, asi que es una referencia para saber si el precio de hoy es
  bueno, no una promesa de poder comprarlo abajo.
- **La plataforma solo se dice cuando no es Steam.** 239 de las 252 ofertas son
  claves de Steam; etiquetarlas todas no informa.

**En el movil la cabecera se rompia**, y es el tipo de cosa que solo se ve
mirandola: desde que dice tambien donde esta mas barato, esa nota mas el precio
mas la pastilla del descuento se comen el ancho, y el titulo -que puede
encogerse hasta cero- se quedaba en una palabra por linea. Por debajo de 560px
el precio baja a su propia linea.

### El grafico y lo que le falta

La linea pasa a ser **el minimo entre la estandar de Steam y las demas
tiendas**. No hubo que tocar el dibujo: `serieDelMinimo()` de `ofertas.js` ya
hace exactamente eso con las tiendas de Ofertas, asi que la serie guarda el
minimo de las otras tiendas como una serie mas, con la llave `__tiendas` (dos
guiones bajos para que no choque con el nombre de una edicion). Se guarda solo
el minimo y no una serie por tienda: son hasta 17 por juego y el grafico dibuja
el minimo de todas formas.

**Lo que hay que saber: la parte de tiendas arranca el 19-09-2026**, asi que en
los juegos con historial anterior la linea baja ahi de golpe. No es un precio
inventado -antes ese dato no se tenia- y el pie del grafico dice el rango y no
una caida, pero el escalon esta y se ira solo en 30 dias.

**Y hay un SEGUNDO escalon el 22-09-2026, al entrar Instant Gaming**, por la
misma razon y con mas fuerza, porque esa tienda suele ser la mas barata: es la
mas barata de su juego en 26 de las 33 ofertas que trajo el primer dia.

```
aeterna-noctis   19-09: 23,89 EUR  ->  22-09: 2,39 EUR
blasphemous      21-09:  5,31 EUR  ->  22-09: 3,19 EUR
```

Los 2,39 EUR de Aeterna Noctis no son una bajada de ese dia: es que hasta ese
dia ese precio no estaba en nuestros datos. Conviene tenerlo escrito porque el
escalon se lee solo como un desplome, y dentro de unos meses nadie se va a
acordar de que ahi entro una tienda.

La regla, que ya vale para el siguiente que se anada: **cada vez que entra una
fuente de precios nueva, la linea del minimo da un escalon el dia que entra**,
y no se siembra hacia atras. Con ITAD se penso y se descarto por lo de aqui
abajo; con Instant Gaming no hay ni de donde, porque su ficha solo dice el
precio de hoy.

**Sembrarlo con `/games/history/v2` se penso y no se hizo**, y conviene saber
por que antes de intentarlo: ese log trae `shop` y `deal` pero **no trae
`drm`**, asi que no se le puede aplicar el filtro de plataforma. Sembrar meteria
en la linea precios de GOG y DRM-Free que esta seccion no publica, o sea
cambiaria un escalon que se explica por una linea que no se corresponde con lo
que hay debajo.

## Instant Gaming: la unica del mercado gris que deja entrar

Anadida el **22-09-2026**, y lo primero que se hizo fue medir las seis que se
pedian (G2A, Kinguin, Gamivo, CDKeys, Eneba e Instant Gaming). **Cinco no
entran, y por tres motivos distintos que conviene no mezclar:**

| | Portada | Por que se queda fuera |
|---|---|---|
| Kinguin, G2A, Gamivo, CDKeys | **403 de Cloudflare** | Es el corte de gg.deals: 403 en la portada ya no es el modo de pedir, es una deteccion |
| **Eneba** | 200 | Su ficha **no miente por accidente, lo avisa**: pone "No es el precio final" |
| **Instant Gaming** | 200 | Entra |

ITAD no era el camino: `GET /service/shops/v1?country=ES` devuelve **34 tiendas
y ninguna es del mercado gris**, asi que no es cuestion de quitarle un filtro.
Allkeyshop, que si las cubre, **permite `/api/latest` en su robots.txt y corta
la conexion** en esa misma ruta; y CheapShark son las mismas 34 de ITAD en
dolares.

**Kinguin y G2A no estan cerradas del todo, y eso hay que leerlo bien**:
`gateway.kinguin.net/esa/api/v1/products` y `api.g2a.com/v1/products` contestan
un **401 JSON limpio**, o sea que la puerta existe y lo que falta es la llave.
Son APIs de revendedor o de afiliado, asi que entrar por ahi es darse de alta
como tal, con la comision de por medio. Es una decision del usuario y no una
cuestion tecnica, y por eso se dejo escrito en vez de intentarlo.

**Eneba es el caso que mas ensena, porque su "no" no es tecnico.** Su ficha
abre, pero el precio solo aparece con navegador y ademas sale con un *"No es el
precio final"* al lado: es un mercado de revendedores que suma comisiones al
pagar, y la misma edicion se vende con clave EMEA o Global, que son productos
distintos. Publicar ese numero seria lo unico que esta seccion no puede hacer.

### Como se lee, y por que no necesita navegador

La ficha trae el mismo bloque `schema.org` que lee `precios.py`, pero servido
ya hecho, asi que `instantgaming.py` sigue siendo solo biblioteca estandar:

```html
<meta itemprop="priceCurrency" content="EUR" />
<meta itemprop="price" content="3.19" data-price-eur="3.19" />
<div class="retail">25&nbsp;€</div>  <div class="discounted">-87%</div>
```

El nombre y la plataforma salen del **BreadcrumbList** (`PC` -> `Steam` -> el
juego) y no del titulo, porque hay juegos con guiones en el nombre y recortarlo
seria adivinar donde acaba.

### El id va escrito en el catalogo porque su buscador esta cerrado

`Disallow: /es/busquedas/` en su robots.txt, y **no publican sitemap**
(`/sitemap.xml` da 404), asi que no hay forma permitida de preguntarle cual es
la ficha de un juego. Los 43 ids se resolvieron a mano el 22-09-2026 con un
buscador externo -sus fichas si estan indexadas- y se congelaron, igual que el
`itad` y que la lista de deseados.

Del id sale la URL sola porque **el slug no cuenta**: `/es/12335-x/` devuelve
200 y la misma ficha que la URL larga. Aun asi lo que se publica es el enlace
canonico que trae la propia pagina.

### Los tres filtros, y el cuarto que aparecio al medir

Los tres primeros eran previsibles y saltaron todos en casos reales:

- **Plataforma**, igual que en `itad.py`: al buscar Cyberpunk 2077 lo unico que
  vende Instant Gaming es la version de **GOG**, asi que ese juego se queda sin
  esta tienda. Kena entra como clave de **Epic**, que tambien se compra.
- **Region**, y es el que mas trabajo dio: vende el mismo juego con clave de
  *Latin America* o *United States*, que no se activa desde Espana. Se lee del
  sufijo del titulo (`"... - PC (Steam) - Latin America"`) y es **lista blanca**,
  por lo mismo que el bloque `tema` de `medios.json`. Se compara **trozo a
  trozo partiendo por `&`**, porque *"Europe & USA & Canada"* es buena y
  *"USA & Canada"* no; comparar la cadena entera tiraba Tales of Graces f.
  Tales of ARISE se quedo fuera por esto: alli solo hay clave de Latin America.
- **Dispositivo**, que vende tambien Switch y PS5 con el mismo nombre.

**El cuarto no se vio venir y es el importante: sin existencias publica el
precio igual.** Cult of the Lamb salia a 8,49 EUR con
`availability: OutOfStock`, y la pagina, en vez del boton de comprar, dice
*"Recibir un e-mail cuando se reponga el stock"*. O sea el precio de algo que
no se puede comprar, que en esta web habria coronado la fila como lo mas
barato del juego. Mewgenics es la version extrema: `OutOfStock` y **precio
`0.00`**, que se habria leido como gratis. Es la cuota de Orange otra vez, un
numero con la forma del campo bueno que no es el precio.

**Y no avisa en el parte**, a diferencia de los otros tres descartes: quedarse
sin existencias es el dia a dia de una tienda de claves, y sacarlo en cada
pasada hasta que repongan es el aviso que sale siempre y se deja de leer. Por
eso `SinExistencias` es una excepcion aparte. El dia que se midio eran **10 de
43**, que es mucho y conviene saberlo: en esta tienda la fila aparece y
desaparece sola, al reves que en las de ITAD.

### Lo que cuesta, y el unico numero que hay que vigilar

No tiene API, asi que es **una peticion por juego**: 43 fichas de media MB con
`PAUSA` de 1,5 s entre ellas, o sea que la pasada pasa de 16 segundos a unos 5
minutos. Por eso `steam.yml` sube su `timeout-minutes` de 10 a 20.

La pausa no es cosmetica: son 43 peticiones a una sola tienda dos veces al dia,
y es la diferencia entre una visita y una rafaga. Es el mismo razonamiento que
`PAUSA_MISMA_TIENDA` en `precios.py` y que el techo de dos pasadas diarias.

### Desde el runner la ficha viene en DOLARES, y no es un bloqueo

Se miro el primer run esperando un 403 como el de PcComponentes, y **no hubo
ninguno**: la tienda responde al runner igual de bien que a un PC de casa. Lo
que pasa es otra cosa y es mas silenciosa: **la moneda la elige la IP**, y el
runner de GitHub esta en Estados Unidos, asi que las 43 fichas llegaron en USD.
Pedir `/es/` pone la pagina en espanol, no en euros.

No se publico ni un precio falso porque la comprobacion de moneda los tiro a
los 43, que es exactamente para lo que estaba: es la misma red que el `cc=es`
de `steam.py` y el `country=ES` de `itad.py`. La pasada salio igual con las 252
ofertas de ITAD, que es el fallo blando funcionando.

**La salida no es un parametro, porque el de la tienda (`?currency=`) esta en
su robots.txt.** Es que la propia ficha publica los dos numeros:

```html
<meta itemprop="price" content="3.19" data-price-eur="3.19" />
```

`content` es lo que se ensena y cambia con la IP; **`data-price-eur` va siempre
en euros**. Se ve mejor en los listados de esa misma pagina, donde los dos van
en pareja (`data-price` al lado de `data-price-eur`), y lo confirma la tabla de
cambio que la ficha lleva dentro: la tienda guarda el precio en euros y
convierte al pintar.

Conviene tener claro por que esto NO contradice el filtro de ITAD que echa a
las tiendas que no cotizan en euros: alli el problema era que el euro lo
calculaba ITAD a partir de un precio en dolares, o sea una conversion ajena al
escaparate. Aqui el euro es el numero original y el dolar el convertido.

**Lo que se pierde fuera de Espana es el precio tachado**, que no tiene gemelo
en euros: es texto pintado en la moneda de la pagina. Se publica sin el y la
web ya sabe no dibujarlo. Reconstruirlo del descuento seria un numero calculado
por nosotros, o sea la etiqueta de "estimado" de Ofertas, y no compensa por un
tachado. **El descuento si vale siempre**, que un porcentaje no tiene moneda.

La leccion, que es la de siempre pero en una variante nueva: aqui **lo que
cambiaba entre los dos sitios no era si te dejan entrar, sino que te sirven**.
El sondeo de "403 en local contra 403 en el runner" no habria visto nada, y lo
unico que lo caza es comprobar el dato que llega, no el codigo de respuesta.

## Lo que falta, y esta decidido que falte

- **Nueve juegos no tienen ficha en Instant Gaming**, y no es un olvido:
  Bloodstained Curse of the Moon, Cyberpunk 2077 (solo lo vende de GOG), Kill
  The Plumber, Little King's Story, Nikoderiko, Pyre, Super Yooka-Laylee Kart,
  Tales of ARISE (solo con clave de Latin America) y There Is No Game.
- **Super Yooka-Laylee Kart es el unico sin objetivo**, y no es un olvido:
  todavia no esta a la venta, asi que no tiene precio contra el que ponerlo.
- **Siete juegos no tenian ninguna otra tienda** cuando se monto ITAD
  (Mewgenics, NEEDY GIRL OVERDOSE, No Rest for the Wicked, Pyre, The Hundred
  Line, The Outbound Ghost y el propio Super Yooka-Laylee Kart). No era un
  fallo: o no se venden en mas sitios, o solo en los que se filtran. Cinco de
  los siete los cubre desde el 22-09-2026 Instant Gaming; siguen sin nada
  **Pyre y Super Yooka-Laylee Kart**.
