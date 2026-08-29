# Mi Criadero

Web de noticias que se actualiza sola. Cinco secciones, dos vistazos al día,
y ni una tecla que tocar.

**https://spaizor.github.io/mi-criadero/**

| Sección | Qué trae |
|---|---|
| 💻 **Tecnología** | Lo del día, sin IA (que tiene la suya) |
| 🤖 **IA** | Modelos, empresas y dinero de la inteligencia artificial |
| 🎮 **Nintendo** | Switch, juegos y todo lo de la casa |
| 🌍 **Geopolítica** | Prensa de fuera del bloque occidental: rusa, china, turca, iraní, asiática y latinoamericana |
| 🏷 **Ofertas** | El precio de 7 juegos en hasta 9 tiendas, con su mínimo histórico y su precio objetivo |

Cada sección guarda además los **días anteriores** con buscador, en `historico.html`.

---

## El horario, que es lo que se viene a mirar

Todo son **horas españolas de verano**. En invierno sale una hora antes: los
relojes de GitHub y de las rutinas van en UTC y no cambian con la hora oficial.
No pasa nada, y por eso no se corrige.

### Por la mañana

```
 4:00  💻 Tecnología
 4:30  🎮 Nintendo
 5:00  🤖 IA
 5:30  🌍 Geopolítica        <- esta solo sale por la mañana
 6:10  🏷 Precios
 7:40  🏷 Precios (repesca, solo si la de las 6:10 no salió)
 9:15  🔍 Vigilancia
 9:30  🔍 Vigilancia (la de fuera de GitHub)
 9:40  🏷 Precios (última repesca)
```

### Por la tarde

```
14:10  🏷 Precios
15:40  🏷 Precios (repesca)
16:00  💻 Tecnología
16:30  🎮 Nintendo
17:00  🤖 IA
17:40  🏷 Precios (última repesca)
21:15  🔍 Vigilancia
```

Así que **a primera hora está todo hecho**: las cuatro secciones de noticias
antes de las 6, los precios a las 6:10 y el parte de si algo ha fallado a las
9:30.

### Por qué van escalonadas y no todas a las 4:00

Porque todas escriben en el mismo repositorio. Si dos terminan a la vez, la
segunda se encuentra la rama cambiada y su publicación rebota. Media hora entre
una y otra sobra para que no se pisen.

---

## Quién hace el trabajo

Son dos mecanismos distintos, y conviene no mezclarlos:

| | Noticias | Precios |
|---|---|---|
| **Quién lo lanza** | Una rutina de Claude, en la nube de Anthropic | GitHub Actions, dentro del propio repositorio |
| **Quién elige** | El modelo: lee, resume y decide qué sale | Nadie. Se lee el precio y se publica |
| **Si falla** | No se recupera: los feeds solo dan lo reciente | Se recupera entero: la tienda sigue teniendo el precio |

### Las noticias

1. Un script descarga los RSS de los medios de la sección y quita lo repetido,
   las guías, las ofertas y lo que no viene a cuento.
2. El modelo abre y lee las mejores, y escribe las **destacadas** (7, u 8 en
   geopolítica y 6 en IA) con su resumen.
3. Los **titulares** de medios españoles los pone el script leyéndolos del feed,
   sin pasar por el modelo: en un medio español no hay nada que traducir, y
   hacerlo pasar por el modelo solo añadía el riesgo de que se invente la hora.
4. Se valida, se archiva una copia del turno y se publica.

**El diseño de la web no lo toca nadie.** Las rutinas solo escriben ficheros
dentro de `data/`, así que una ejecución que salga mal puede dejar una sección
sin noticias, pero no puede romper la página.

### Los precios

Se abre la ficha de cada tienda y se lee el precio del bloque de datos que las
tiendas publican para Google, no del texto de la página. Cuatro de las nueve
tiendas hay que abrirlas con un navegador de verdad, porque a un script le
contestan que no.

Tres tiendas (**Amazon, El Corte Inglés y Fnac**) salen solo con su enlace, sin
precio. Las dos últimas porque no responden; Amazon porque su normativa no
permite sacarle el precio con un script, aunque técnicamente se pueda. Enlazar
a la ficha sí es correcto, y eso es lo que se hace.

---

## Las repescas de precios, explicadas

GitHub llega tarde a sus propias citas: medido sobre un mes, **nunca** ha
disparado a la hora, y el retraso normal va de media hora a una. Eso da igual.
Lo que no da igual es que algunos días **no dispara**, y una cita que no ocurre
no falla ni avisa de nada.

La solución es pedirlo tres veces y quedarse con la primera que llegue:

```
        6:10 ─────────► ¿hay precios de esta mañana?
                             │
                    no ──────┴────── sí
                     │                │
              consulta las         se para
              tiendas y            (10 segundos,
              publica  ✅          no hace nada)


        7:40 ─────────► la misma pregunta
        9:40 ─────────► la misma pregunta
```

En un día normal trabaja la de las 6:10 y las otras dos son un vistazo de diez
segundos. Si la de las 6:10 no llega a salir, trabaja la de las 7:40. Y si
tampoco, la de las 9:40.

Por eso **una repesca que no hace nada es lo normal y sale en verde**. Solo hay
aviso si se han consultado las tiendas de verdad y no ha contestado ninguna.

---

## La vigilancia: enterarse el mismo día

El problema de fondo de todo esto es que **un fallo silencioso no se nota**. Una
rutina que no arranca no deja rastro; un cron que no dispara no falla. La única
señal es que ese día falta algo, y para verla hay que acordarse de mirar.

Así que hay tres vigilantes, y están a propósito en sitios distintos:

| Cuándo | Quién | Qué hace si algo falta |
|---|---|---|
| 9:15 y 21:15 | GitHub Actions | Deja el aviso en el registro de ejecuciones |
| 9:30 | Una rutina de Claude | Pinta una **banda roja en la portada** |
| Siempre | El propio trabajo | Si una tienda no responde, la ejecución queda en rojo |

El de las 9:30 vive **fuera de GitHub** por un motivo concreto: el día que lo
que falla es GitHub, el vigilante que vive en GitHub calla también. Ya pasó.

Y ese vigilante no solo avisa: al publicar su aviso **relanza los precios**, que
es la única de las dos cosas que se puede recuperar.

---

## Ver la web en local

Con doble clic en el HTML **no funciona**: el navegador bloquea la carga de los
JSON. Hace falta un servidor:

```
python -m http.server 8765
```

Y abrir http://localhost:8765

---

## Comandos

Ninguno hace falta para el día a día: esto se lanza todo solo. Están para
cuando algo se tuerce.

```
python3 scripts/noticias.py estado        ¿se ha publicado el turno de hoy?
python3 scripts/noticias.py comprobar     ¿está bien dada de alta cada sección?
python3 scripts/noticias.py vigilar       las tres comprobaciones de golpe
python3 scripts/precios.py consultar      traer los precios ahora
python3 scripts/precios.py frescura       ¿falta la pasada de precios que tocaba?
```

Los precios necesitan Playwright para las tiendas que piden navegador:

```
pip install playwright && playwright install chromium
```

---

## Qué hay en cada sitio

```
index.html            la portada
<seccion>.html        una por sección, todas iguales por dentro
historico.html        días anteriores, con buscador
assets/               el estilo, el JavaScript y los iconos
data/                 lo único que reescriben las rutinas
data/historico/       una copia de cada turno, desde el 07-08-2026
scripts/noticias.py   todo el trabajo mecánico de las noticias
scripts/precios.py    lo mismo para los precios
scripts/medios.json   qué medios lee cada sección
scripts/productos.json  qué juegos se siguen y en qué tiendas
```

El detalle de por qué cada cosa está hecha como está, y las decisiones que no
hay que deshacer sin leerlas antes, viven en `CLAUDE.md`.
