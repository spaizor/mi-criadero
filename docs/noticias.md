# scripts/noticias.py

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

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

## El comando `titulares`: los medios espanoles no pasan por el modelo

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

## La hora de `actualizado` la pone el script, no el modelo

Desde el **12-09-2026**. El campo `actualizado` decide de que turno es el
fichero (`partir_actualizado`: antes de las 12:00 es M, despues es T), o sea que
el dato mas estructural del JSON dependia de que el modelo acertara una hora que
no tiene por que saber.

No la acerto. Al pasar las rutinas a Haiku, las horas se fueron: el turno de la
manana de nintendo del 11 y el 12-09-2026 se ejecuto a las 4:40 y llego con
`14:30` dentro, asi que se archivo como **turno de tarde** y `estado` dio por
perdida la manana que si se habia publicado. Lo mismo en las otras secciones
(`01:15` en una ejecucion de las 5:02, `09:00` en una de las 4:08). Lo que se ve
es un falso "M FALTA" cada dia, que es justo el aviso que sale siempre y se deja
de leer.

`sellar_actualizado()` lo escribe del reloj, en hora espanola. Es la misma regla
que ya separo los titulares espanoles del modelo: **un dato que el script puede
leer no se le pide a quien puede inventarlo**.

- **Se sella en `titulares` y en `archivar`, no en `validar`**: validar solo
  mira. Que lo repita `archivar` es lo que cierra el agujero el dia que
  `titulares` no llegue a correr, porque archivar lo lanzan todas las secciones
  siempre y es el que decide el nombre del fichero del turno.
- **En `titulares` va despues de la comprobacion de turno ya archivado**, no
  antes: esa comprobacion mira el `actualizado` que trae el fichero para saber
  si es el del turno pasado, y sellarlo primero le borraria la pista.
- **Con `--probar` no se sella**, que ese modo promete no tocar el fichero.
- `validar` avisa (no error) si el desfase pasa de 2 h: el fichero se publicara
  bien igual, pero ese desfase dice que `titulares` no ha corrido o que lo que
  hay en `data/` es de otro turno.
- Efecto de paso: la comprobacion de "fecha posterior a la hora de ejecucion"
  de las destacadas vuelve a servir. Con un `actualizado` puesto a las 23:59 no
  cazaba nada.

Lo que **sigue saliendo del modelo** es la hora del mensaje de `publicar`
(`"Actualiza noticias de Nintendo (DD-MM-AAAA HH:MM)"`), que por eso puede no
cuadrar con la del commit. No molesta a nada: ese texto no lo lee ningun script.

## El comando `estado`

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

## El buscador del historico

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
