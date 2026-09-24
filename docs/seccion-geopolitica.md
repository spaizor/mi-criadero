# La seccion de Geopolitica

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

Abierta el **28-08-2026**. Medios de fuera del bloque occidental: rusos, chinos,
turcos, iranies, asiaticos y latinoamericanos, mas la prensa occidental no
alineada. Es la seccion **mas ancha del proyecto**: 32 medios vivos y **236
candidatos por turno**, contra los 84 de tecnologia y los 18 de `ia`. Por eso
lleva **8 destacadas**, una mas que nintendo: aqui el numero lo permite lo que
hay, al reves que en `ia`, donde se bajo a 6 porque no daba.

## Sale una vez al dia, y por eso `secciones.json` declara los turnos

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

## No lleva filtro de tema, y menos aun filtro geografico

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

## Los medios: se eligen, no se filtran

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

## `descartado`: el aviso que salia siempre

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

## TRT World publicaba los enlaces relativos

Su feed da `/article/e12d692b1e86` en las 100 entradas, no la URL entera, y asi
llegaba al JSON: un enlace roto en la web. Lo caza `validar`, pero para entonces
la noticia ya esta escrita y hay que rehacerla. Desde el 28-08-2026
`entradas_del_feed` acepta la portada del medio como base y resuelve el enlace con
`urljoin`, que no toca los que ya son absolutos. Es el unico medio de los 32 que lo
hace, pero el arreglo va en el sitio comun porque el siguiente feed que lo haga
entraria igual de callado.

## El ruido de los medios en espanol: `excluir_categorias`

Los `idioma: es` **no pasan por el modelo**, se publican tal cual sale del feed. Son
5 (Sputnik Mundo, teleSUR, Resumen Latinoamericano, Prensa Latina, Anadolu Espanol)
y cubren de sobra la destacada espanola que exige `validar`. En la primera pasada
colaron *"Carlos Alcaraz debutara ante Roman Safiullin en el US Open"* y una pelicula
dominicana, y se dejo sin filtro a proposito hasta tener historico.

**Medido el 23-09-2026 sobre los 237 titulares suyos publicados desde el 28-08**,
clasificados a mano uno a uno: **36 eran ruido (15%)**, no uno de cada cuatro. Y el
ruido no se reparte igual: Prensa Latina colo 14 de 38 y teleSUR 12 de 64, y
los otros tres casi nada (Sputnik 5 de 59, Anadolu 3 de 37, Resumen
Latinoamericano 2 de 39).

La herramienta es el `<category>` del feed, que es la clasificacion del redactor y
no una adivinanza, o sea lo mismo que `excluir_rutas` pero leido en otro sitio. De
ahi `excluir_categorias`, un campo del medio en `medios.json` que se aplica en
`candidatos` y en `titulares`. Hoy lleva **una sola categoria por medio**:

- **teleSUR `Deporte`** y **Prensa Latina `Deportes`**: los 8 publicados con esas
  categorias eran los 8 ruido (la liga de beisbol, los Juegos Suramericanos, el
  remo de Brisbane), y en la portada de la categoria de teleSUR, 30 de 30 eran
  deporte.
- **`Cultura` no, en ninguno de los dos**, aunque en lo publicado pareciera ruido
  puro. Es la leccion de `/streaming-tv/` otra vez: en la portada de la categoria
  teleSUR mete *"Ministro de Cultura israeli pide despojar de ciudadania a los
  directores de Naza"* y el boicot a Israel en Venecia, y Prensa Latina el debate
  italiano sobre alumnos extranjeros por aula.
- Se compara **el nombre entero**, no un trozo, porque WordPress mete en
  `<category>` las etiquetas junto a las categorias.

**Anadolu si categoriza en la URL** (`/es/mundo/`, `/es/turkiye/`, `/es/deportes/`),
al reves de lo que se creyo al montar la seccion. Pero **`/es/turkiye/` no se puede
excluir**, y es el mismo error evitado por tercera vez: en lo publicado parecia
ruido (el naufragio de Girne, un congreso forense en Antalya) y en el feed del dia
eran 12 de 30 entradas, casi todas diplomacia de Erdogan en la Asamblea de la ONU.

**Lo que sigue entrando, y no hay corte que lo quite**: 28 de los 36. Son sucesos y
clima locales (un huracan, un incendio en Quito, un simulacro en Mexico),
efemerides y felicitaciones oficiales cubanas y venezolanas, y propaganda de
provincias chinas. Van en la misma categoria que lo bueno (*America Latina y El
Caribe*, *Nota Informativa*), y Sputnik y Anadolu no declaran categoria. Solo lo
quitaria el modelo, que es justo lo que se aparto de estos titulares para que no
inventara horas ni fuentes. Con un 12% de ruido, compensa.
