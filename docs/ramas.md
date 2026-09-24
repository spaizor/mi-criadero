# Las ramas que dejan las rutinas

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

Cada ejecucion de una rutina trabaja en su propia rama `claude/<nombre>` y
publica con `git push origin HEAD:main`. La rama no se borra sola: el
19-09-2026 habia **69**, unas seis al dia desde el 07-09.

Se pueden borrar todas sin pensarlo, y la comprobacion que lo demuestra es
`git branch -r --no-merged origin/main`, que ese dia dio **0**: ninguna tenia un
solo commit que no estuviera ya en `main`. Una rama de rutina es el camino por
el que paso el turno, no el sitio donde vive.

Lo hace `.github/workflows/limpiar-ramas.yml`, los lunes. Como en Precios y en
Steam, **no lo lanza una rutina de Claude**: aqui no se elige nada, y borrar una
rama es quitar un puntero. Dos cautelas, que son lo unico que hace falta
entender del fichero:

- **Solo borra lo fusionado en `main`** (`git merge-base --is-ancestor`). La que
  tenga algo propio se queda y lo dice. Que se acumule una rama de sobra no le
  molesta a nadie; borrar lo unico que quedaba de un trabajo, si.
- **Y solo lo de hace mas de dos dias**, para no llevarse por delante la rama de
  una rutina que este corriendo en ese momento.

`workflow_dispatch` admite `dias` y `probar`, que lista lo que borraria sin
tocar nada. Probado el 19-09-2026 sobre las 69: 58 a borrar y 11 que se quedaban
por recientes.

**La opcion de GitHub que parece servir y no sirve** es *Automatically delete
head branches*: solo actua sobre ramas de pull requests fusionados, y aqui las
rutinas empujan directo a `main` sin abrir ninguno.
