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
python3 scripts/noticias.py hecho      <seccion>   si el turno de ahora ya salio (paso 0)
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
- `validar` comprueba los enlaces **sin abrirlos** (`validar_enlaces`). Antes
  solo miraba que empezaran por `http`, y asi se publicaron tres destacadas
  cuyo enlace era la portada del medio (`nintendowire.com`, `vandal.net`,
  `telesureng.net`): la rutina no habia podido abrir el articulo y puso lo que
  tenia. Son dos pruebas:
  - **ERROR si el enlace no tiene ruta**, solo el dominio. Vale para
    destacadas y titulares.
  - **Que el dominio sea el del medio**, segun `web` y `feed` de
    `medios.json`. ERROR en las destacadas y AVISO en los titulares: el enlace
    de un titular sale del feed y no del modelo, y si un medio cambia de
    dominio un error obligaria a quitar titulares buenos hasta que alguien
    corrija `medios.json`. Con las fuentes que no estan en `medios.json` (lo
    buscado por fuera) no hay con que comparar y no se mira.

  Medido el 01-10-2026 sobre las 7.662 noticias del historico: la primera caza
  las tres conocidas y nada mas; la segunda, una destacada y tres titulares
  del 10-09 firmados como `teleSUR` con enlace de `telesurenglish.net`, que es
  otro medio de la lista (`teleSUR English`). Ningun falso positivo. No se
  hace con una peticion al enlace porque los medios que dan 403 a los scripts
  (Nintendo Wire) saldrian siempre como rotos.
- `validar` **avisa de las destacadas de mas de 48 horas**. `candidatos` ya
  descarta lo viejo, pero lo que el modelo busca por fuera no pasa por ahi: el
  07-09 entro una de MacRumors con doce dias. Es aviso y no error porque un
  tema que sigue vivo puede merecer el sitio. Una fecha a las 00:00 significa
  "el articulo no dice la hora", asi que se cuenta desde el final de ese dia.
  En el historico salta en 14 destacadas de 1.989, repartidas en 6 turnos de
  328, casi todos de fin de semana; ninguno despues del 14-09.
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
- `anteriores` y `candidatos` **ponen la copia al dia con `origin/main`** antes
  de leer el historico (`poner_al_dia`). Lo repetido se decide con el historico
  de la copia local, y el 08-10-2026 la rutina de IA arranco 29 commits por
  detras: su "turno anterior" era del 05-10, le salieron 74 candidatos en vez de
  unos 20 y se le colo un titular publicado el 06-10. `validar` lee la misma
  copia y no lo vio; salto en el rebase de `publicar`, y el modelo acabo
  editando `indice.json` a mano para resolver el conflicto. El mismo rastro hay
  en tecnologia el 23 y 24-09: 7 enlaces repetidos entre turnos seguidos, que
  con la copia al dia habrian caido en la ventana de `anteriores`.
  - Solo avanza con **fast-forward y la copia sin cambios**, que es como empieza
    cualquier rutina, y lo dice en una linea. Si hay cambios o commits propios,
    avisa y no toca nada: ese rebase lo decide quien trabaja en la copia.
  - **No va en `validar` ni en `titulares`**: a esas alturas otras rutinas ya han
    publicado en main lo suyo, y el aviso saldria casi siempre por commits que
    no son de esta seccion.
  - Sin red no dice nada: no hay con que comparar, y `candidatos` ya avisa de
    los feeds caidos.

## El comando `titulares`: los medios espanoles no pasan por el modelo

En un medio espanol **no hay nada que traducir**: el titulo del feed ya es
publicable. Hacerlo pasar por el modelo solo anadia el riesgo de siempre —
horas y fuentes inventadas— en la mitad del contenido. Asi que el reparto de
trabajo es ahora este:

1. `candidatos` da la materia prima.
2. El modelo escribe `data/<seccion>.json` con **las destacadas y los
   titulares de los medios de fuera**, que si hay que traducir.
3. `titulares <seccion>` anade los de los medios `"idioma": "es"` leyendolos
   del feed, les pone a las destacadas la hora del feed y reescribe el fichero.
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
- **Pone la fecha y hora de las destacadas**, desde el 02-10-2026
  (`poner_horas_del_feed`). Es lo unico que toca de ellas. La hora la buscaba
  el modelo en el articulo, y ese dia nintendo salio con 6 de sus 7 destacadas
  a las 00:00: la pagina decia "hace 8 horas" y el prompt mandaba poner 00:00
  si no habia hora. El dato ya estaba en el feed (`publicado` en la salida de
  `candidatos`). Medido sobre las 39 destacadas de los ultimos turnos que
  seguian en el feed: **34 coincidian al minuto, y en las 5 que no la buena era
  la del feed** (las 3 de las 00:00, y una de Nintendo Life y otra de The
  Register con la hora britanica de la pagina sin convertir). Por eso pisa
  siempre y no solo las 00:00.
  - Solo toca las que tienen **el enlace tal cual en el feed de su medio**. Lo
    traido de fuera con WebSearch, o un titular viejo que asciende, se queda
    con la fecha del modelo, y para esas sigue valiendo la regla del 00:00.
  - Se hace en `titulares` y no despues porque los feeds son cortos: horas mas
    tarde, 44 de las 83 destacadas medidas ya no estaban (Nintenderos trae 9
    entradas, The Verge 10).
  - Una fecha del feed posterior a la hora de ejecucion no se aplica: `validar`
    la daria por error y nadie podria corregirla.

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
https://claude.ai/code/routines antes del turno siguiente. Lo que evita que se
pierda es la repesca de abajo.

## La repesca: cada rutina se dispara dos veces por turno

Desde el **08-10-2026**, por el turno de tarde de IA del 07-10, que no llego a
publicarse: ni commit ni rama `claude/`, con tecnologia y Nintendo saliendo
normales esa misma tarde y el mismo prompt funcionando la manana de antes y la
de despues. Medido sobre el historico: **desde el 12-09-2026, 1 turno perdido
de 182** entre las cuatro secciones, y tecnologia no ha perdido ninguno nunca
(los seis de IA y Nintendo del 6 al 11-09 son de la semana en que se estaban
cambiando las rutinas). O sea que no es el prompt.

El log de esa ejecucion lo explica: el modelo hizo el turno entero (validado y
archivado) y **GitHub devolvio un error 500 a todos los push** durante mas de
tres minutos, a `main` y a su rama, hasta que la sesion se rindio con el commit
solo en local. No se corto ni dejo de arrancar: se quedo sin poder publicar.

Lo que lo tapa sea cual sea la causa es lo mismo que en precios ("Los cron de
repesca" en `docs/vigilancia.md`): si la primera no dispara, dispara la
siguiente. Cada rutina de noticias lleva en su cron una segunda hora por turno,
una hora despues de la suya, y su prompt empieza por un **PASO 0**:

```
python3 scripts/noticias.py hecho <seccion>
```

Mira en `origin/main` si el turno de ahora (`M` antes de las 12:00 y `T`
despues, el mismo corte que `partir_actualizado`) ya esta en el indice del
historico. Si esta, contesta **TERMINA** y la rutina acaba ahi; si no,
**SIGUE** y hace el turno entero. Con la hora del fallo, el 07-10 a las 18:10,
da SIGUE en IA y TERMINA en Nintendo, que es lo que tenia que pasar.

| Rutina | cron (UTC) |
|---|---|
| Noticias tecnologia | `0 2,3,14,15 * * *` |
| Noticias Nintendo | `30 2,3,14,15 * * *` |
| Noticias IA | `0 3,4,15,16 * * *` |
| Noticias Geopolitica | `30 3,4 * * *` |

El prompt y el cron viven en https://claude.ai/code/routines, no en el repo, y
**una sesion de Claude en la nube no puede editarlos**: esas rutinas se crearon
por la API y no las creo un agente, asi que `update_trigger` se niega (probado
el 08-10-2026). Se cambian a mano en la web o con `/schedule update` desde el
CLI, que es ademas lo unico que admite un cron a medida.

Cuatro decisiones:

- **En la misma rutina, no en una aparte.** Una rutina de repesca que lanzara a
  las demas seria otra pieza que puede fallar, y tendria que conocer sus
  identificadores. Asi cada rutina se cubre sola. Lo que cuesta: siete
  ejecuciones cortas mas al dia en la lista de sesiones, que acaban en el
  PASO 0.
- **Una hora despues.** Las ejecuciones tardan de 2 a 7 minutos, asi que no se
  pisan; queda margen de sobra antes de `LIMITE_TURNO` (9:00 y 21:00) y los
  feeds siguen teniendo lo de esa hora. Una hora es ademas el intervalo minimo
  que admite el cron de una rutina.
- **Ante la duda, SIGUE.** Si el comando falla o no existe, la rutina hace el
  turno; si no hay red, `hecho` lee la copia local, que es un clon recien
  hecho. Hacer un turno dos veces no rompe nada (`archivar` sustituye la
  entrada repetida del indice y reescribe el fichero del turno); quedarse sin
  hacer es justo lo que esto viene a tapar.
- **El veredicto va en el texto y el codigo de salida es 0 siempre.** Lo lee el
  modelo, que toma un codigo 1 por un comando roto. Al reves que `estado`, que
  lo lee un workflow.

Lo que **no** tapa es que fallen las dos. Por ejemplo, si se agota el uso de la
suscripcion durante horas: las rutinas gastan del mismo que las sesiones a mano,
y sin margen se rechazan. O si caduca la conexion con GitHub. Para eso sigue
`estado`.

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
