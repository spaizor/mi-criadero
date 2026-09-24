# Icono, manifest y previsualizacion

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

La web se lee en el movil todos los dias, asi que desde el 21-08-2026 se
instala como una app: `manifest.json` en la raiz, iconos en `assets/` y las
metas en el `<head>` de las seis paginas.

**El icono lo genera `scripts/iconos.py`, no un editor de imagenes.** Los
colores de las secciones salen de `assets/estilo.css` (`--acento-tec`,
`--acento-ia`, `--acento-nin`, `--acento-geo`, `--acento-ofe`), asi que el dia
que cambie el acento de una seccion se regenera con `python3
scripts/iconos.py` en vez de repintarlo a mano. Escribe el PNG a mano con
`zlib` y `struct`, que para figuras planas son treinta lineas, y asi el script
sigue la regla del proyecto de no depender de nada que no sea la biblioteca
estandar.

El dibujo es **el criadero que da nombre a la web**: un monticulo con su
abertura y, delante, un huevo por seccion con el color de esa seccion. Sin
letras a proposito: a 32 px una inicial no se lee, y una silueta con manchas de
color si se reconoce entre veinte pestanas.

## El dibujo: de la rejilla al criadero (30-08-2026)

Hasta ese dia eran los cuatro colores de seccion en un 2x2. Lo cambio la quinta
seccion: `iconos.py` se planta a proposito si el dibujo no admite las secciones
que hay, asi que **desde geopolitica el icono estaba congelado**, con los cuatro
colores viejos y sin poderse regenerar. El criadero quita ese techo, porque los
huevos se reparten en dos filas y salen de `secciones.json`.

Cinco cosas que hay que saber antes de tocar el dibujo:

- **Es un criadero generico, no el de ningun juego, y eso es deliberado.** La
  idea vino de las estructuras organicas de la estrategia espacial, pero lo que
  esta protegido es el diseno concreto de cada una: aqui la silueta es propia,
  la paleta es la de la web y en el repositorio no se nombra ningun juego ni
  ninguna marca. Un nido con huevos no lo invento nadie; una copia de uno
  concreto si tiene dueno.
- **Todas las piezas son elipses, incluida la cupula**, que es una elipse
  cortada por la linea del suelo. No es una limitacion de gusto: es lo unico que
  los PNG y el SVG saben pintar identico sin aproximar nada -por distancia al
  borde aqui, con `<ellipse>` y un `<clipPath>` alli-. Una curva mas libre
  obligaria a rasterizar poligonos en un lado y a escribir bezieres en el otro,
  o sea dos descripciones del mismo dibujo, que acaban siendo dos dibujos.
- Por lo mismo, **el dibujo se declara una sola vez**, en `formas()`, y de ahi
  salen los seis ficheros. Antes cada formato tenia su codigo y no molestaba
  porque eran cuatro cuadrados.
- **Los hombros no son adorno.** Con una sola elipse cortada, la silueta sale
  como un arco de circo perfecto y se lee antes como un arcoiris que como algo
  vivo. Son dos elipses mas bajas a los lados, y con eso ya es un monticulo.
- **La abertura va ancha, achatada y con aro por encima**, y las tres cosas se
  decidieron mirandolas a 16, 24, 32 y 48 px, que es donde se usa el icono:
  estrecha se lee como un mordisco en el contorno y no como un agujero; alta y
  pegada al borde superior deja una franja fina que convierte el conjunto en el
  asa de un bolso. Su color es cosa aparte y esta mas abajo, con lo del fondo
  transparente.

La leccion es la de siempre en este proyecto, aplicada al diseno: **el icono se
juzga al tamano al que se usa, no a 512 px**. Las tres correcciones de arriba se
veian todas en la tira de 16 a 48 px y ninguna en el grande.

## Sin fondo, y encajado en el cuadro (30-08-2026)

El icono nacio con una pastilla oscura redondeada detras, heredada del 2x2, y
con eso se veia pequeno: entre el margen y el aire que dejaba un dibujo
apaisado, la silueta ocupaba poco mas de la mitad del cuadro. Ahora **el
favicon y los dos PNG del manifest van con fondo transparente**, que ademas es
lo correcto en una pestana o un escritorio claros, donde la pastilla se ve como
un parche pegado.

Tres cosas que eso arrastra, y ninguna es opcional:

- **La abertura ya no puede ser del color del fondo.** Lo era, y funcionaba
  mientras hubiera pastilla; sin ella, esa elipse #0f1115 se convierte en una
  mancha oscura flotando sobre lo que haya detras. Es su propio tono
  (`BOCA`), un ciruela oscuro que se lee como agujero contra el blanco y contra
  el negro, y que sigue valiendo en los dos iconos que si van opacos.
- **El maskable y el de Apple siguen opacos, y no por descuido.** Android le
  aplica su forma al maskable y una esquina transparente se veria recortada;
  iOS directamente rellena de negro la transparencia. Son los dos unicos
  ficheros con fondo, y por eso el dibujo tiene que quedar bien de las dos
  maneras.
- **El dibujo se encaja, no se mide en fracciones del lado.** `formas()` dibuja
  en coordenadas propias y `encajar()` calcula su marco y lo centra y escala
  hasta llenar el lienzo. Hacia falta porque **el ancho depende de cuantas
  secciones haya** -cada huevo nuevo ensancha la fila-, o sea que ninguna medida
  fija podia estar bien para todos los casos. Y el marco se mide con el suelo
  puesto: las elipses cortadas no llegan adonde llegaria su radio, y sin eso el
  dibujo sale pequeno y subido.

Cuatro cosas que hay que saber para no romperlo:

- **El "maskable" lleva mucho mas margen que los demas** (20% contra 4%).
  Android recorta ese icono a un circulo y solo garantiza el 80% central: con
  el margen normal le cortaria los hombros al monticulo.
- **El de Apple va cuadrado y opaco.** iOS redondea el icono el solo y no lleva
  bien la transparencia: se la rellena de negro. Y lleva algo mas de margen que
  los sueltos (10%) porque ese redondeo se come las esquinas.
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
