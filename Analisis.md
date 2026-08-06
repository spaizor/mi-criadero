# Plan: Miniweb automatizada con Claude + GitHub Pages

## Objetivo
Tener una página web con varias secciones (por ejemplo: tecnología, política, fútbol) cuyo contenido se actualiza automáticamente cada día mediante tareas programadas de Claude, sin coste alguno.

## Idea clave
La web (estructura, diseño, botones, menú) es HTML normal y corriente, creada una sola vez. Las tareas programadas de Claude no reconstruyen la web: solo entran a actualizar el contenido de secciones concretas dentro de ella.

## Piezas del sistema
- **GitHub**: aloja el código de la web (repositorio) y, con GitHub Pages activado, la publica de forma gratuita.
- **Claude (Cowork, tareas programadas)**: genera el contenido y lo sube al repositorio. Corre en la nube de Anthropic, no depende de tener el móvil o el PC encendido.
- **Conector de GitHub en Claude**: permite que Claude suba archivos directamente al repositorio.

## Pasos a seguir

### 1. Crear el repositorio y la estructura de la web
- Crear un repositorio en GitHub.
- Crear un `index.html` (portada) con los botones/enlaces a cada sección.
- Crear un archivo HTML por sección (ej. `tecnologia.html`, `politica.html`, `futbol.html`).

### 2. Activar GitHub Pages
- En el repositorio: **Settings → Pages**.
- Elegir la rama (normalmente `main`) y la carpeta donde está el HTML.
- Guardar. GitHub genera una URL pública del tipo `usuario.github.io/nombre-repo`.

### 3. Conectar GitHub a Claude
- En Claude: **Settings → Connectors → GitHub**.
- Autorizar el acceso al repositorio. Este paso se hace una sola vez.

### 4. Crear las tareas programadas en Claude
- Una tarea programada por sección (tecnología, política, fútbol), cada una con su propio horario.
- Cada tarea debe indicar: buscar la información correspondiente, generar el HTML actualizado, y subirlo/actualizarlo en el archivo correcto del repositorio.
- A la hora programada, Claude ejecuta todo el proceso solo: busca, redacta y sube el archivo usando el conector.

### 5. Histórico de contenido (opcional)
- Opción recomendada: en vez de sobrescribir siempre el mismo archivo, guardar cada resumen con la fecha en el nombre (ej. `tecnologia-2026-07-31.html`), y enlazar desde la sección un listado de fechas anteriores.
- GitHub también guarda automáticamente el historial de cambios (commits), aunque eso no se ve "bonito" en la web sin la opción anterior.

## Sobre el coste
- No se usa la API de Claude (que es de pago por token): todo corre dentro de la cuota ya incluida en la suscripción Pro/Max, a través de Cowork.
- GitHub es gratuito para este uso: repositorio público + GitHub Pages sin coste.

## Resultado final
Una URL pública (tipo `usuario.github.io/nombre-repo`) que el usuario puede visitar cuando quiera desde el móvil, con las secciones actualizadas automáticamente cada día sin intervención manual.
