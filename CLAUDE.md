# Mi_Criadero

Web estatica de noticias publicada en **GitHub Pages**, cuyo contenido actualiza
sola una rutina programada de Claude en la nube.

- URL publica: https://spaizor.github.io/mi-criadero/
- Repositorio: https://github.com/spaizor/mi-criadero (rama `main`)

## Ojo: este proyecto NO sigue las reglas del contenedor

A diferencia del resto de carpetas de `c:\GitHub`, aqui **no hay Python, ni
`.venv`, ni `main.py`, ni empaquetado con PyInstaller**. Es HTML, CSS y JS
estatico. No busques un interprete ni intentes lanzarlo con `python main.py`.

Para verlo en local hace falta un servidor web (abrir el `index.html` con doble
clic falla por CORS al cargar los JSON):

```
python -m http.server 8765
```

## Idea clave: el HTML no se toca nunca

La estructura y el diseno se crearon una sola vez. Las tareas programadas
**solo reescriben un JSON** dentro de `data/`. Esto evita que una ejecucion
automatica rompa el diseno.

```
index.html            portada con los botones de seccion
tecnologia.html       seccion (carga data/tecnologia.json)
nintendo.html         seccion (carga data/nintendo.json)
assets/estilo.css     estilo compartido, claro/oscuro, responsive
assets/noticias.js    hace fetch del JSON y pinta las tarjetas
data/*.json           <-- lo unico que tocan las rutinas
```

Al anadir una seccion nueva: copiar un HTML de seccion, cambiar el titulo, el
`data-seccion` del `<body>` (define el color de acento en el CSS) y la ruta del
JSON, y anadir su tarjeta en `index.html`.

## Formato de los JSON de contenido

Cada seccion tiene dos niveles: **5 destacadas** que la rutina abre y lee, y
hasta **25 titulares** que salen del listado del medio sin abrir el articulo.
Los titulares se pintan en un bloque plegable debajo de las destacadas.

```json
{
  "seccion": "tecnologia",
  "actualizado": "DD-MM-AAAA HH:MM",
  "destacadas": [
    {
      "titulo": "Titular en espanol",
      "resumen": "2-3 frases con los hechos concretos",
      "fuente": "Nombre del medio",
      "enlace": "https://...",
      "fecha": "DD-MM-AAAA HH:MM"
    }
  ],
  "titulares": [
    {
      "titulo": "Titular en espanol",
      "fuente": "Nombre del medio",
      "enlace": "https://...",
      "fecha": "DD-MM-AAAA"
    }
  ]
}
```

Todas las fechas en hora espanola. **Los titulares llevan fecha sin hora a
proposito**: como no se abre el articulo, no hay forma de saber la hora de
publicacion, y pedirsela solo consigue que se la invente.

Si los dos arrays estan vacios, la pagina muestra un aviso de "todavia no hay
noticias" en lugar de romperse. `assets/noticias.js` acepta ademas el formato
antiguo (un unico array `noticias`) como respaldo, para que la web no se quede
en blanco entre un cambio de formato y la primera ejecucion de la rutina.

## Publicacion

GitHub Pages esta configurado como *Deploy from a branch* → `main` → `/ (root)`.
Cualquier push a `main` republica la web, pero **tarda 1-2 minutos**. Si un
cambio no se ve al instante, esperar antes de darlo por fallido.
