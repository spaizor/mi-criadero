# scripts/medios.json y el comando `candidatos`

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

`medios.json` es la lista de medios por seccion, con su RSS. **No esta en
`data/`** a proposito: ahi lo publicaria `publicar` si una ejecucion lo tocara
por error. Solo se usan los medios con `"comprobado": true` y `feed` no nulo;
el resto se ignoran, asi que un medio roto nunca rompe una ejecucion.

`candidatos` descarga esos feeds y devuelve, en JSON, lo publicado **desde el
turno anterior** (fecha que saca del indice del historico), ya sin lo repetido
ni lo que huele a guia u oferta. De ahi salen los titulares: titulo, enlace y
fecha vienen del feed, no del criterio del modelo, que es justo donde antes se
inventaban las horas. El campo se llama `titulo_original` para que se note si
alguien lo copia sin traducir.

Las lineas que empiezan por `#` son el parte de la descarga y hay que leerlas:

- `FEED CAIDO <medio>`: no ha respondido esta vez. Reintentar suele bastar.
- `SIN FEED <medio>`: no tiene RSS utilizable y hay que abrirlo a mano. Ahora
  mismo son Nintendo Wire (403 a los scripts hasta en la portada) y Meristation
  (su feed responde, pero la ultima entrada es de febrero de 2023).

La lista es el **minimo**, no el techo: si un dia da poco, se busca ademas por
fuera. Y `candidatos` no cubre las destacadas, que siguen exigiendo abrir y
leer el articulo.

## Un medio "que bloquea a los scripts" casi nunca bloquea

Vandal estuvo meses fuera con la nota de que su servidor cortaba la conexion a
los scripts aunque el feed funcionase en un navegador. Era falso. Lo que manda
es el feed **con gzip sin que se lo pidan**, y como `descargar` no lo
descomprimia, lo que llegaba eran bytes binarios que el parser rechazaba como
XML invalido. Por eso `descargar` mira ahora el numero magico `1f 8b` ademas de
la cabecera `Content-Encoding`, que no todos la mandan bien.

3DJuegos estaba fuera con un "no publica RSS" sacado de probar `/rss/`,
`/rss.xml`, `/feed/` y `/noticias/rss/`. Si lo publica: en
**`/feedburner.xml`**, igual que Xataka, y **lo declara su propia portada**.
Adivinar rutas no lo iba a encontrar nunca; leer el HTML del medio, si.

Las dos lecciones valen para el proximo medio que parezca cerrado:

- **Antes de dar un medio por bloqueado, mirar que llega de verdad.** Un fallo
  de parseo no es un bloqueo, y los dos se cuentan igual en el parte. Volcar el
  tamano y los primeros bytes lo resuelve en un minuto.
- **La ruta del feed se lee, no se adivina.** Esta en el `<link>` de la portada
  o en el HTML; probar rutas a ciegas solo descarta las que se te ocurren.

Un 403 de verdad, ese si existe: Nintendo Wire lo da en las cuatro rutas **y en
la portada**, asi que ahi no es el feed ni la compresion.

## Y un "no" que no es tecnico: mirar el robots.txt

Al valorar ocho medios el 14-08-2026, tres venian con la nota de que bloqueaban
a los scripts (El Chapuzas "402", TechPowerUp "deteccion de bots", Nintendo
World Report "su robots.txt prohibe el acceso automatico"). **Los tres
descargaron a la primera**, o sea que las tres notas eran falsas. El robots.txt
de Nintendo World Report son 34 bytes con un `Crawl-delay` para msnbot: no
prohibe nada.

Pero **TechPowerUp si prohibe**, y ese es el motivo por el que se quedo fuera.
Ahora bien, hay que leer **cual** de los dos "no" es, porque son distintos y
confundirlos deja una regla que este proyecto se salta en 8 sitios.

**El "no" por nombre no nos aplica.** Casi todos los medios grandes llevan
bloques del tipo `User-agent: ClaudeBot` -> `Disallow: /`. Eso le habla a un
rastreador concreto, el que Anthropic pasea por la web por su cuenta. Nuestro
script no es ese: se lanza cuando lo lanza la rutina y **pide el RSS**, que es
un fichero que el medio publica justamente para que lo lean programas y lo citen
con enlace. Prueba de que no va con nosotros: ninguno de ellos cierra el feed.
Quien no quiere que le lean cierra de verdad, como Nintendo Wire, que da 403
hasta en la portada.

Si ese bloque contase como veto, habria que echar a **TechCrunch, The Verge,
Areajugones, Nintendo Everything, The Register, 404 Media y Nintenduo**: son
8 de los 26 medios activos, medido el 15-08-2026. O sea, media seccion de
tecnologia por una regla que nadie estaba aplicando.

**El "no" general si nos aplica.** El de TechPowerUp no nombra rastreadores:
dice que esta prohibido *"any device, tool, or process designed to data mine or
scrape the content using automated means... without prior written permission"*.
Eso no habla de IA, habla de **cualquiera que automatice**, y `candidatos` es
exactamente eso. Su punto (1), el "text and data mining" del Art. 4 de la
Directiva europea, es la clausula que permite a un medio reservarse ese derecho,
y ese robots.txt es la reserva. **El Chapuzas** esta en la misma zona por
`ai-train=no`.

Ojo con citar el punto (2) de TechPowerUp ("the development of any software,
machine learning, AI and/or LLMs") como motivo: habla de **desarrollar o
entrenar** modelos, que es justo lo que aqui no se hace. El (4), "commercial
purposes", tampoco, porque la web no monetiza.

Asi que el criterio, en una linea: **veta la prohibicion general de automatizar,
no el bloqueo por nombre de rastreador.** Y el feed respondiendo no es permiso,
igual que en Amazon: ahi el limite tampoco era tecnico.
