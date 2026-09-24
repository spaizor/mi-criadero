# Los filtros de los feeds

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

## El filtro por tema

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

### Ampliar la lista `tema`: el peligro es colar, no quedarse corto

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

## El filtro por seccion de la URL: `excluir_rutas`

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

### Medir lo publicado no basta: `adslzone.net/noticias/streaming-tv/`

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

## `excluir_en_ruta`: cuando la categoria mezcla dos cosas

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
