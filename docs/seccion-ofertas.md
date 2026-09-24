# La seccion de Ofertas

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

No busca ofertas: sigue el precio de una lista cerrada de productos, que vive
en `scripts/productos.json`. `scripts/precios.py consultar` abre cada ficha,
lee el precio y escribe `data/ofertas.json`.

Como aqui no se elige nada, esta seccion **no la actualiza una rutina de Claude
sino `.github/workflows/precios.yml`**: lanza el script, y si ha entrado algun
precio publica reutilizando `noticias.py publicar`. Si no entra **ninguno**, no
publica y falla el job a proposito: seria un commit diario marcando todo como
viejo sin haber mirado nada, y ademas taparia el aviso de que las tiendas han
empezado a bloquear al runner.

## Anadir un producto son dos pasos, y el segundo se olvida

El catalogo que lee la pasada es el de **`origin/main`**, no el del disco: quien
abre las fichas es el runner. Asi que tras tocar `scripts/productos.json` hay
que **empujar el commit** y despues **lanzar `Precios` a mano** (`gh workflow run
precios.yml --ref main`, o el boton de Actions).

El segundo paso hace falta porque el `on: push` de `precios.yml` **solo escucha
`data/vigilancia.json`**, que es lo que le da su papel de pistoletazo de la
vigilancia: subir el catalogo no dispara nada. Y `workflow_dispatch` es ademas
lo unico que se salta el guardia de frescura, o sea lo unico que consulta aunque
la pasada del tramo ya este hecha. Sin ese lanzamiento, el producto nuevo no
aparece hasta el cron siguiente.

**Lo que despista cuando se olvida el primer paso** (paso el 18-09-2026 con
Metroid Ravenous, y costo tres intentos): la web no falla ni avisa de nada, y
lanzar el workflow **tampoco**, porque corre tan feliz sobre el catalogo viejo y
acaba en verde. Lo unico que se ve es que `data/ofertas.json` tiene un producto
menos que `scripts/productos.json`, y eso se lee como un fallo del script cuando
en realidad son dos ficheros que no tienen por que coincidir: uno es la entrada
y el otro la salida de la ultima pasada. Antes de buscar el fallo en el codigo,
**mirar `git status -sb` y de que commit sale el run**.

**El job lleva `timeout-minutes` porque un fallo mudo ya paso.** El 19-08-2026
el paso de instalar Playwright se quedo colgado y el job estuvo **seis horas**
ahi hasta que GitHub lo mato por su limite; la pasada de la manana se perdio.
Lo peor no fue perderla sino que **un run cancelado no avisa**: el fallo solo
se vio al revisar el historial dos dias despues. Con el tope, un cuelgue acaba
en fallo, y un fallo si manda correo. La ejecucion normal tarda 3-4 minutos, o
sea que 20 no aprieta nada.

**Y el aviso de "ninguna tienda ha respondido" saltaba sin haber mirado nada.**
Los dias 28 y 29-08-2026 el job acabo en rojo cuatro veces con
`Ninguna tienda ha respondido:  consultas, 0 precios`, y el hueco donde va el
numero era la pista: no es que las tiendas bloqueasen al runner, es que el
guardia de las repescas habia dicho que la pasada del tramo ya estaba hecha y
**no se abrio una sola ficha**. Al saltarse el paso de contar, su salida `ok`
queda vacia, y **las expresiones de GitHub comparan laxo como JavaScript**, asi
que `'' == '0'` es cierto y el paso de avisar se disparaba solo. Se arregla
mirando ademas `steps.salud.outcome == 'success'`.

Lo que hace grave a este fallo no es el correo de mas: es que el aviso dice
justo lo contrario de lo que pasa, y **es el unico aviso que hay para el dia en
que las tiendas cierren de verdad**. Un vigilante que grita cuando no ocurre
nada se acaba ignorando, y entonces callara tambien el dia bueno. Lo mismo vale
para el resto del fichero: **un `if` sobre la salida de un paso que puede
saltarse tiene que mirar tambien si el paso corrio**, porque en GitHub vacio y
cero valen igual.

## `precios.py tiendas`: la tienda que se cierra ella sola

El aviso de arriba solo salta cuando no responde **ninguna** tienda, asi que la
que se cierra ella sola no pone nada en rojo: sus precios se quedan marcados
como `viejo`, la web los pinta con su fecha al lado y no se entera nadie.
PcComponentes estuvo asi **doce dias**, del 10 al 22-09-2026, y lo que lo
descubrio fue que alguien se puso a mirar, que es justo lo que un vigilante
existe para no tener que hacer. Es el tercer fallo mudo de esta seccion,
despues del cron que no dispara y del cuelgue de Playwright, y va por el mismo
sitio: el job falla y GitHub manda el correo.

**El umbral esta medido, no elegido**, sobre las 107 pasadas publicadas entre el
08-08 y el 22-09-2026:

| Tienda | Racha mas larga sin un solo precio |
|---|---|
| Orange | nunca fallo una pasada |
| Carrefour, GAME, Xtralife | 1 pasada (0,0 dias) |
| MediaMarkt | 2 pasadas (0,2 dias) |
| **PcComponentes al cerrarse** | **29 pasadas (11,9 dias)** |

Entre el bache normal y la averia hay **dos ordenes de magnitud**, o sea que
cualquier corte intermedio vale y el numero no es delicado. Se eligen **7 dias**
(`DIAS_SIN_PRECIO`) porque con eso no salta ni una falsa alarma en el historico
entero ni aunque una tienda pase un fin de semana caida, y aun asi PcComponentes
habria avisado el 17-09, cinco dias antes de que se viera a mano.

Cuatro cosas del comando:

- **Va por ficha, aunque el mensaje se agrupe por tienda.** Asi caza tambien la
  ficha suelta que se queda atras porque la tienda retiro el producto o le
  cambio la URL, que es el mismo agujero en pequeno.
- **No mira los `nuevo`**, o sea las fichas que no han dado precio jamas: no
  traen fecha desde la que contar, y se ven solas en el parte del dia en que se
  anaden, que es cuando se esta mirando. Por eso PcComponentes salia como 7
  fichas y no 8: la de Leyendas Pokemon Z-A nunca llego a dar precio.
- **El texto del error dice que mirar y en que orden**, que es donde viven las
  explicaciones largas en este proyecto: del 403 que mide *como* pides, a
  repetir la ficha desde un PC de casa, a bajarla a `solo_enlace`. Solo se
  pagan el dia que algo falla.
- **El aviso vuelve a salir cada dia hasta que se arregle o se baje la tienda, y
  eso es a proposito.** Aqui no vale el truco de la ventana de `estado`, porque
  esto no caduca: mientras no se haga ninguna de las dos cosas sigue siendo
  verdad, y la accion que lo calla es justamente la decision que hay que tomar.
- En el workflow los dos avisos llevan **`!cancelled()`**: son averias distintas
  y ninguno puede quedarse sin salir porque el otro haya puesto el job en rojo
  antes. Y los dos siguen exigiendo que `salud` corriera, por lo del 28-08-2026.

El precio **no se saca leyendo la pagina**, sino del bloque `schema.org/Product`
que las tiendas incrustan para Google. Las dos formas conviven y hay que cubrir
las dos: GAME lo publica en una etiqueta `<script type="application/ld+json">`
indentada, y MediaMarkt comprimido dentro del estado interno de la pagina, sin
etiqueta. Como una ficha trae ademas variantes y productos relacionados con sus
propios precios, se elige el bloque que contiene la referencia numerica de la
URL pedida.

## Un 403 no dice que la tienda este cerrada

Durante dos dias se dio por hecho que MediaMarkt y PcComponentes filtraban las
**IP de datacenter**: daban precio desde casa y 403 desde el runner, y de ahi
salio `solo_enlace`. Era falso, y la forma de verlo fue pedir la misma ficha
**dos veces desde el mismo sitio y en el mismo segundo**, una con `urllib` y
otra con Chromium. Medido el 10-08-2026 desde el runner:

| Tienda | urllib | Chromium | En el catalogo |
|---|---|---|---|
| GAME | 59,99 EUR | 59,99 EUR | si, sin navegador |
| MediaMarkt | 403 | **50,99 EUR** | si, con `navegador` |
| PcComponentes | 403 | **50,99 EUR** (403 en 1 de 3) | ya no, ver abajo |
| Xtralife | pagina sin precio | **52,95 EUR** | si, con `navegador` |
| Carrefour | 403 | **50,99 EUR** | si, con `navegador` |
| El Corte Ingles, Fnac | 403 | 403 | no |

Lo que filtran es **parecer un script**, no la direccion. Misma IP, mismo
minuto, distinto resultado: eso descarta la IP como explicacion. La leccion
util es que un 403 mide *como* pides, no si te dejan; antes de descartar una
tienda hay que repetir con `--navegador`. De las cinco descartadas con la
teoria vieja, Carrefour cayo a la primera.

### Y sin embargo PcComponentes si era la IP, dos anos despues

**Esto no deshace lo de arriba, lo acota**, y hay que leer las dos cosas juntas
para no volver a equivocarse en ninguna de las dos direcciones. El 10-08-2026 la
IP no era la explicacion, y se demostro. El **10-09-2026** PcComponentes empezo a
dar 403 en sus 8 fichas y dejo de darlo **nunca mas**: 12 dias y unas 24 pasadas
sin una sola excepcion, o sea ya no el 403 intermitente que documenta
`Navegador.html()`.

Medido el 22-09-2026 separando las dos variables que quedaban, y sale redondo:

| | Portada | Ficha en frio | Calentando la portada |
|---|---|---|---|
| **Runner**, urllib | 403 | 403 | — |
| **Runner**, Chromium de Playwright | 403 | 403 · 403 · 403 | 403 |
| **Runner**, Chrome de verdad | 403 | 403 · 403 · 403 | 403 |
| **PC de casa**, Chromium de Playwright | 200 | **200 · 200 · 200, con precio** | 403 |

Mismo dia, mismo codigo, misma receta. Tres cosas que deja esto:

- **El corte sigue siendo la portada**, el mismo que fijo gg.deals: el 403 llega
  con `<title>Just a moment...</title>` y `challenges.cloudflare.com`, o sea un
  challenge, y ahi ya no es el modo de pedir. Saltarlo seria evadir una
  deteccion, que es la linea que este proyecto se puso con Amazon.
- **Cambiar de canal no solo no arregla: rompe lo que funciona.** En la misma
  medicion, el control de Carrefour dio **200 con el Chromium de Playwright y
  403 con Chrome de verdad**. Si algun dia se piensa en `channel="chrome"`,
  esto dice que no.
- **La receta en frio sigue siendo la buena.** Calentarle la portada le da 403
  tambien desde casa, igual que el 13-08-2026, asi que `Navegador._contexto()`
  esta bien como esta.

Asi que desde el 22-09-2026 esta con `solo_enlace`, como El Corte Ingles. **Y sin
su ultimo precio**: de los 8 congelados el 09-09, tres ya eran falsos trece dias
despues (Octopath 26,99 cuando eran 33,99), y un precio que no se va a refrescar
nunca envejece hacia la mentira por mucho que lleve la fecha al lado.

Lo que esto ensena para la proxima tienda que caiga es a **distinguir el fallo
que se repite del que persiste**. Un 403 suelto, o 12 de 14, mide como pides. Un
403 que no falla ni una vez en semanas y que alcanza a la portada es otra cosa, y
la forma de saber cual es la de siempre aqui: pedir lo mismo desde dos sitios.

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

## El precio objetivo, la serie y los avisos

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
- **Una tienda que se deja de consultar no puede seguir marcando el minimo.**
  La serie no caduca (cada tienda mantiene su ultimo precio hasta el punto
  siguiente) y `ultimosDias()` mete ese valor dentro de la ventana por antiguo
  que sea, asi que PcComponentes habria dibujado su 50,99 de agosto para
  siempre. `serieDelMinimo()` acepta desde el 22-09-2026 un segundo argumento
  con las tiendas vigentes, que son las que no estan en `enlace`. **Las `viejo`
  si cuentan**: esas se siguen mirando y no respondieron hoy, que es justo
  cuando el ultimo precio conocido es la mejor referencia. Y **no se borra nada
  de la serie**, porque aquellos precios fueron ciertos: lo que deja de valer es
  darlos por vigentes. Steam la llama sin ese argumento y no cambia.
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

## La entrada de la portada: lo que esta a punto de caer

Cambiado el **22-09-2026**, y vale igual para Ofertas y para Steam porque el
fallo era el mismo. La entrada coronaba el precio mas bajo (Ofertas) y la mayor
rebaja (Steam), y las dos acababan diciendo siempre lo mismo: el juego mas
barato del catalogo. Ese dia salian **Octopath a 28,95 EUR**, que llevaba
catorce dias igual y con su objetivo a un 45% de distancia, y **Blasphemous a
5,31 EUR al -79%**, que es un descuento espectacular sobre un juego que nunca
vas a mirar. Un -79% no dice si eso esta cerca o lejos de lo que pagarias.

Ahora la entrada contesta a otra pregunta, que es la que se viene a hacer:
**cual esta mas cerca de su precio objetivo**. Cuatro decisiones:

- **La distancia se mide en proporcion, no en euros.** En euros gana siempre lo
  barato: a un juego de 5 EUR con objetivo 3 le faltan 2, y a uno de 60 con
  objetivo 50 le faltan 10, aunque el segundo este mucho mas cerca. Se ve en los
  datos del dia: por euros Steam corona NEEDY GIRL OVERDOSE (le faltaban 1,51) y
  por proporcion SteamWorld Heist II, al 50% de su meta.
- **Los ya cumplidos no entran**, porque esos suben solos a la banda de avisos,
  arriba y en verde. Repetirlos abajo gastaria la entrada en decir dos veces lo
  mismo, que es lo que ya pasaba con Metroid Ravenous.
- **Los que no tienen objetivo quedan fuera**, que es lo que hace que esto
  funcione: sin una meta no hay distancia que medir. En Ofertas la tienen los 9;
  en Steam, 43 de 52 en su estandar.
- **En Steam cuentan tambien las ediciones y los bundles con objetivo propio**,
  al reves que el resumen de rebajas, y no es una incoherencia: una Deluxe al
  -70% sigue costando mas que la estandar y coronarla seria vender como chollo
  el producto caro, pero **una Deluxe a 4 EUR de SU precio esta a 4 EUR de su
  precio**. Probado forzando la Ultimate de Cyberpunk: sale como
  `Cyberpunk 2077 (Ultimate Edition)`.

**El aviso y el resumen salen de la misma funcion** (`metasDeSteam` y
`metasDeOfertas`, que devuelven cada objetivo junto al precio con el que hay que
compararlo). Calcularlo dos veces es como acabarian diciendo cosas distintas del
mismo juego el dia que se toque una y no la otra. De ahi cuelga tambien la regla
de contra que precio se compara cada objetivo, que no es obvia: **la estandar
contra el mas bajo en cualquier sitio** (si ha llegado a tu precio en Fanatical,
ha llegado) y **las ediciones especiales solo contra Steam**, porque ITAD da el
precio del JUEGO y no el de su Deluxe.

Los tres finales de la entrada dicen cosas distintas a proposito: *"Hoy no ha
respondido ninguna tienda"* es una averia, *"Todos tus precios objetivo estan
cumplidos"* es la mejor noticia posible, y el normal es la meta mas cercana. Los
dos primeros dejan la entrada apagada, y no pasa casi nunca; los tres estan
probados a mano sobre el JSON.

## Como lo pinta `assets/ofertas.js`

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
