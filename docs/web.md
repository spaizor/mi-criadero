# La web: estilo, series de precios y numero de version

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

## `serie_desde`: no pedir el mes que no existe

El grafico de precios necesita **el mes en curso y el anterior**, porque 30 dias
cruzan el cambio de mes, y los dos JS los pedian siempre los dos. En una seccion
recien abierta el de antes no existe, asi que cada visita dejaba un **404 en la
consola**: a Ofertas le paso en agosto de 2026 y a Steam desde que nacio, el
18-09, pidiendo `data/steam-precios/2026-08.json` en cada carga.

No rompia nada -el `catch` ya devuelve una serie vacia y los precios de hoy se
pintan igual-, pero un error que sale siempre en la consola es lo mismo que un
aviso que sale siempre: cuando aparezca uno de verdad, estara entre el ruido.

**No se puede tapar desde el JavaScript**, que es lo que se penso primero: el
navegador pinta el error de red antes de que el `fetch` conteste, asi que la
unica forma de no verlo es **no pedir el fichero**. Por eso `consultar` escribe
en el JSON de la seccion el campo `"serie_desde"` con el primer mes del que hay
serie, y la web descarta lo anterior. Es lo mismo que ya hacia el buscador del
historico, donde **los meses que hay que pedir salen del indice** en vez de
adivinarse.

- **Es el PRIMER mes y no la lista entera**, para que el campo no crezca con los
  anos: a la web le basta con eso para descartar lo que no existe.
- **Se saca listando el directorio de series**, no de una constante con la fecha
  de apertura: asi vale igual para las dos secciones y no hay nada que recordar
  actualizar.
- **Si el JSON no lo trae, se piden los dos meses como antes.** Hace falta de
  verdad: el fichero publicado no lo lleva hasta la siguiente pasada, y sin ese
  respaldo la web se quedaria un rato sin graficos.
- En `steam.py` el JSON de salida se escribe **antes** que la serie del mes, o
  sea que en la primera pasada de un mes nuevo ese mes todavia no tiene fichero.
  Da igual, porque lo que se guarda es el primero y no el ultimo.

Probado con los dos: Steam pasa a pedir un solo mes y sigue pintando sus 51
graficos, y Ofertas sigue pidiendo los dos, que es lo correcto porque los tiene.

## El numero de version del pie

Puesto el **22-09-2026**. El pie de las ocho paginas lleva un `v1.3` que abre un
panel con lo que trajo cada version. Sirve para acordarse de que cambio y
cuando, que con la web creciendo dos meses ya no se tenia en la cabeza.

**La numeracion sube una decima por SECCION nueva**, que es la regla que pidio
el usuario y la unica que no hay que discutir cada vez:

| | | |
|---|---|---|
| **1.0** | 08-08-2026 | El arranque: Tecnologia, Nintendo, Ofertas e historico |
| **1.1** | 21-08-2026 | IA (y con ella la portada, el buscador y la app) |
| **1.2** | 28-08-2026 | Geopolitica (y la banda de vigilancia, y el icono) |
| **1.3** | 18-09-2026 | Steam (y despues ITAD y la portada por objetivo) |

Lo que entra **entre** dos secciones se lista dentro de la version abierta, o
sea la de arriba, y la fecha de cada una es la del dia en que se abrio, no la
del ultimo cambio que trae. Por eso 1.1 dice 21-08 y lleva dentro el precio
objetivo, que es del 23.

**Ojo con IA**: la web arranco el 07/08-08-2026 con tecnologia, nintendo y
ofertas, e IA se abrio dos semanas despues, el 21-08. Se penso meterla en la
1.0 por ser "de las de siempre" y se descarto: con la regla de una version por
seccion, la excepcion habria que explicarla cada vez que alguien mire el
historial.

Tres decisiones de como esta montado:

- **La version vive SOLO en `assets/version.json`.** Escribirla ademas en el
  HTML obligaria a tocar las ocho paginas cada vez que sube, que es la clase de
  trabajo repetido que este proyecto evita: subir de version es anadir una
  entrada al JSON y nada mas. El `_instrucciones` de dentro dice como.
- **Va en `assets/` y no en `data/`**, por lo mismo que `medios.json`: ahi lo
  publicaria `publicar` si una ejecucion lo tocara por error.
- **Si el fetch falla, no sale el enlace y el pie se queda como estaba.** Es lo
  contrario de lo que hace `index.html`, que lleva sus entradas escritas para no
  quedarse en blanco, y la diferencia es deliberada: alli lo que se protege es
  el contenido de la pagina, y aqui lo que se perderia es una nota al pie. Una
  version a medias seria peor que ninguna.

El panel es un **`<dialog>` nativo**, por lo mismo que los productos de Ofertas
son `<details>`: trae gratis el cierre con Escape, el foco atrapado dentro y el
fondo inerte. Lo unico a mano es el clic en el fondo, que el `<dialog>` recibe
el mismo y hay que mirar si cayo fuera de su caja. Probado en las ocho paginas,
en claro y en oscuro, y a 390 px de ancho.

**Los cambios se escriben para quien usa la web, no para quien la programa.** Un
arreglo interno que no se ve en pantalla no va al panel: la lista de los tres
fallos mudos de precios, por ejemplo, esta en este fichero y no ahi.

## El estilo Criadero

El **24-09-2026** se cambio la presentacion de la web, no su contenido. La de
antes era correcta pero generica: la misma tarjeta gris con una raya de color a
la izquierda en todas las paginas, la letra del sistema y emojis como unica
senal de cada seccion, que en Windows salen diminutos y desiguales. Se hicieron
maquetas de tres direcciones con los datos reales del dia (Kiosco, de
periodico; Criadero, sacada del icono; Teletipo, densa y con la hora a la
izquierda) y se eligio **Criadero**. Se aplica por fases, revisando cada una en
local antes de subirla:

1. Base comun: colores, letras, barra de arriba y huevos en vez de emojis.
2. Portada: la fecha, el nido de huevos con las novedades y los avisos juntos.
3. Las secciones de noticias.
4. Ofertas y Steam.
5. Historico, panel de version y repaso del tema claro.

### Fase 1: la base comun

- **La paleta sale del icono.** El fondo tira al ciruela del nido y los acentos
  son los huevos, algo menos saturados que los primeros (el rojo de Nintendo
  era `#e60012`) para que seis colores juntos no se peleen. `iconos.py` lee el
  primer valor de cada `--acento-*` y el `--fondo`, asi que **el icono se
  regenero** con los colores nuevos. En tema claro los acentos van mas oscuros:
  los del oscuro, sobre blanco, no dan contraste para un texto pequeno.
- **Las letras se sirven desde `assets/fuentes/`**, no desde Google Fonts:
  asi la web no depende de un servidor de fuera y la app instalada las tiene
  igual. Bricolage Grotesque para los titulos y Figtree para el texto, las dos
  variables (un fichero por familia cubre todos los pesos) y solo con el
  subconjunto latino, que ya trae tildes, enes y signos de apertura. Pesan 97 KB
  entre las dos. Licencia OFL, junto a cada fichero.
- **La barra de arriba sustituye a los chips de la portada y al "← Inicio"** de
  las secciones: desde cualquier pagina se salta a cualquier otra. El logo con
  su enlace a la portada va **escrito en cada HTML**, y las pastillas las anade
  `assets/barra.js`. Si ese JS no carga se pierde el atajo, pero no el camino de
  vuelta.
- **`barra.js` lleva su propia lista de secciones** en vez de leer
  `secciones.json`: leerla seria un fetch, y la barra apareceria despues que el
  resto y empujaria la pagina hacia abajo. Se ejecuta mientras se lee la pagina,
  sin `defer`, para que salga ya completa. La repeticion la vigila `comprobar`,
  que da error si una seccion no esta en esa lista.
- **La pagina actual se saca de la URL**, no del `data-seccion` del `<body>`: el
  historico lo cambia al pasar de pestana y marcaria como actual una seccion en
  la que no se esta.
- **El huevo es una mascara CSS** (`--forma-huevo`) pintada con el `--acento` de
  donde este: un solo dibujo vale para las seis secciones y los dos temas, y no
  hay que tocar el HTML para ponerlo delante de un titulo. Por eso el campo
  `emoji` salio de `secciones.json`: ya no lo leia nadie.
- En Steam el nombre del juego, que enlaza a su ficha, salia con el azul y el
  subrayado del navegador, o en morado si ya se habia visitado. Ahora hereda el
  color del titulo.

### Fase 2: la portada

- **El dia en grande arriba**, con la fecha de quien mira y no la de la ultima
  actualizacion: lo que se pregunta al abrir la portada es que hay de nuevo
  hoy, y la hora de cada seccion ya va en su entrada. Lo escribe `portada.js`;
  sin JS se queda el nombre de la web.
- **El nido**: un huevo por seccion, lleno si tiene algo sin ver y hueco si no.
  En las de noticias es la misma marca "nuevo" de su entrada. **En Ofertas y
  Steam es un aviso de precio**, porque la marca "nuevo" no la llevan: su JSON
  se reescribe dos veces al dia cambie algo o no, y el huevo saldria siempre
  lleno. Un aviso sale muy poco, que es lo que tiene que significar un huevo
  lleno.
- **El nido sale de las entradas de la portada**, no de una lista propia: su
  orden, su color, su enlace y su nombre. Una seccion nueva aparece en el nido
  sola en cuanto tiene su entrada, sin otro sitio que tocar al darla de alta.
- **Los avisos van en una sola caja, una linea cada uno**, en vez de una caja de
  color por aviso: tres cajas grandes antes de la primera noticia se comian la
  pantalla del movil. Cada linea lleva un circulo con un signo (`!` vigilancia,
  `€` precio cumplido, `↓` bajada en Orange) en el color de a donde lleva, y la
  de vigilancia ademas la linea tenida de ambar.
- **Las entradas pierden la raya de la izquierda** y llevan el color de su
  seccion en un degradado desde la esquina, con el huevo delante del nombre.
  Siguen en lista y no en rejilla, por lo que ya se decidio: en rejilla cada
  caja se estira a la mas alta de su fila.
- **Entre la cifra y el `€` va un espacio que no se parte**: en el movil el
  titular de Ofertas dejaba "39,95" al final de una linea y el `€` al principio
  de la siguiente.
