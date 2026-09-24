# Vigilancia: los fallos que no avisaban

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

Dos agujeros del mismo tipo, tapados el 23-08-2026 con la misma idea que ya
habia arreglado el cuelgue de Playwright: **convertir un fallo mudo en uno
ruidoso**.

## `.github/workflows/vigilancia.yml`

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

## `precios.py frescura`: el cron que no dispara

Anadido el **27-08-2026**, y por un caso real. `precios.yml` ya falla cuando
ninguna tienda responde, pero eso solo cubre **las veces que llega a
ejecutarse**: ese dia GitHub no lanzo su cron de las 6:10 y la seccion se quedo
con los precios de la tarde anterior sin que hubiera un job en rojo ni un
correo. **Un cron que no dispara no falla**, que es el mismo tipo de agujero que
ya taparon `estado` y el `timeout-minutes` de Playwright.

`frescura` mira el `actualizado` de `data/ofertas.json` y sale con codigo 1 si
falta la pasada que ya tocaba. Lo lanza `vigilancia.yml` detras de `comprobar`,
con `if: always()`, y tambien `noticias.py vigilar`.

### Medir la antiguedad no valia: el 28-08-2026 el fallo tapaba al vigilante

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

## Los cron de repesca: GitHub no dispara a su hora nunca

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

**Medido otra vez el 15-09-2026: el retraso ya no son 40 minutos, son unas
cuatro horas y media, y todos los dias.** Desde el 29-08 no se ha saltado ni un
cron (seis runs `schedule` cada dia), pero el de las 6:10 crea el run entre las
10:35 y las 11:46 espanolas, y las repescas detras. Como la vigilancia pasa a
las 9:38, **cada manana ve la pasada pendiente y la lanza su push**: en la
practica, la pasada de manana la hace el `on: push`, y los cron llegan despues
y el guardia los despacha en segundos. No es una averia ni hay que adelantar
los cron para compensar. Lo que si hay que saber es que un disparo diario es lo
normal, y que por eso "otro disparo hoy" no puede leerse como "el de ayer no
sirvio", ver la banda que decia lo contrario, mas abajo.

## `noticias.py vigilar`: el vigilante que no vive en GitHub

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

### Y desde el 28-08-2026 no avisa de los precios: los lanza

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

### El disparador de verdad: el push de la propia vigilancia

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
**Comprobado el 30-08-2026, y funciona.** Era lo que faltaba por ver del
28-08: que el push de una rutina dispare workflows depende de con que credencial
empuje, y no habia ningun `on: push` en el repositorio con el que haberlo visto
antes. Ese dia GitHub no lanzo ni el cron de precios ni el de `vigilancia.yml`
(cero runs con `event: schedule` en toda la madrugada), la rutina publico el
aviso a las 09:38, y en el historial de Actions aparece detras `Precios` con
`event: push`, que publico los precios a las 09:40. Dos minutos de principio a
fin, sin tocar nada.

Lo que **no** cubre: si GitHub Actions esta caido del todo, el dispatch tampoco
entra. Pero eso ya no es un fallo mudo, porque la llamada devuelve el error y
entonces si se pinta la banda.

### La banda que decia lo contrario que la linea de debajo

Lo que costaba esta via era que **la banda de aviso salia igual**, y se quedaba
hasta la vigilancia del dia siguiente aunque los precios se hubieran arreglado
dos minutos despues. Con el token no habria pasado, porque entonces el aviso no
llega a escribirse, y se dio por el precio de no guardar una credencial.

El 30-08-2026, viendolo funcionar de verdad, se vio que no era un precio
aceptable: la portada **se contradecia a si misma**. La banda decia *"Falta la
pasada de precios de las 06:10"* justo encima de la entrada de Ofertas, que
`portada.js` pinta con su hora y que ese rato decia *"hoy 09:40"*. De las dos
cosas, la falsa era la que gritaba, y esa es la manera de que se deje de leer la
banda para el dia en que diga algo.

El fallo no era pintar de mas, era de logica, y estaba en el `if` de `vigilar`:
lo escrito ahi es que **si el problema se esta corrigiendo solo, la banda no
sale**, pero ese `if` solo conocia un lanzador, el del token. Desde el 28-08 hay
un segundo que si funciona -este push- y el codigo no se habia enterado, asi que
caia siempre por el `else` de "nadie lo va a arreglar".

Por eso `vigilancia.json` lleva desde el 30-08-2026 **dos listas**:

```json
{ "comprobado": "30-08-2026 09:38", "avisos": [], "disparos": [
    { "que": "precios", "texto": "Falta la pasada de precios de las 06:10..." } ] }
```

- **`avisos` es lo que se pinta**: lo que sigue roto y necesita una persona.
- **`disparos` no se pinta**, y ahi esta la gracia: el fichero cambia igual, o
  sea que hay commit y hay push, o sea que `precios.yml` arranca lo mismo. Le da
  igual el contenido, su `paths` mira el nombre del fichero. El pistoletazo se
  conserva entero y lo unico que se quita es la banda.
- **Un disparo pasa a aviso cuando el disparo anterior no sirvio**, o sea si
  desde esa vigilancia **no ha entrado ninguna pasada** de precios. Esa es la
  unica version del mensaje que no puede quedarse mintiendo. Ojo: no basta con
  que falte la pasada otra vez. El 15-09-2026 el cron fallo dos mananas
  seguidas, los dos disparos funcionaron, y la segunda vigilancia leyo el
  disparo de ayer como "no sirvio" y pinto banda encima de los precios que su
  propio push acababa de traer. Por eso se compara el `actualizado` de
  `ofertas.json` con el `comprobado` del disparo, y no la antiguedad del disparo.
- **Turnos y secciones no pasan nunca por `disparos`**: un turno perdido no se
  recupera y una seccion a medias no se arregla sola. Ahi la banda es el unico
  canal, y por eso no se quito entera, que era la otra opcion encima de la mesa.

Lo que se pierde son **los dos minutos** entre que se escribe el disparo y acaba
el run: ahi falta la pasada y no hay banda. Es asumible porque las dos formas de
que eso acabe mal ya avisan: si el run falla es un job en rojo con su correo, y
si no llega a correr, la vigilancia de manana lo ve y esa vez si pinta.

El mensaje del commit tambien cambia (`"Vigilancia: falta la pasada de precios,
la lanza este push"` en vez de `"1 aviso"`): decir "aviso" en el historial de un
commit cuyo unico cometido es lanzar la pasada seria mentir en el mismo sitio.

## `assets/secciones.json` y el comando `comprobar`

Dar de alta una seccion toca **ocho sitios** (su HTML, el chip y la entrada de
`index.html`, tres reglas de `estilo.css`, `medios.json` y el `indice.json` con
su `desde`), y el problema no es que sean muchos: es que **olvidarse de uno no
rompe nada de forma visible**. Sin su bloque en el historico la seccion funciona
pero no tiene dias anteriores; sin el `desde`, `estado` reclama turnos de antes
de que existiera. Los dos aparecen semanas despues.

`secciones.json` es ahora la lista buena. **La leen** `historico.html` (las
pestanas), `scripts/iconos.py` (un huevo del icono por seccion, en ese orden) y
`comprobar`.
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

**El icono ya no pone techo al numero de secciones**, pero sigue teniendo uno:
lleva un huevo por seccion y `iconos.py` se planta por encima de ocho, que es
donde el huevo deja de llegar a un pixel en la pestana. Antes eran cuatro
cuadros en rejilla y se planto con geopolitica, ver mas abajo.
