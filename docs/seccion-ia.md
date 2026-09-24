# La seccion de IA

*Sacado del `CLAUDE.md` el 24-09-2026, sin cambios. Cuando el texto dice "este fichero", "mas arriba" o "mas abajo", habla de la documentacion del proyecto en conjunto: el resto esta en las demas paginas de `docs/`.*

Abierta el **21-08-2026**, sacandola de tecnologia. La idea de partida era otra
—dividir tecnologia en IA y hardware— y lo que la cambio fue medir las 680
noticias de tecnologia ya publicadas y la materia prima de 48 h de sus feeds:

| | Publicado | Materia prima | Por turno |
|---|---|---|---|
| IA | 26% | 14% | 9,5 |
| Hardware | 13% | 11% | 7,2 |
| Ni una ni otra | **59%** | **74%** | 49,5 |

Los dos motivos por los que la division en dos no se hizo estan en esa tabla:

- **Partir en IA y hardware no reparte, amputa.** Casi tres cuartas partes de
  lo que hay no es ni una cosa ni la otra: espacio, ciberseguridad, telecos,
  redes sociales, software, juicios, centros de datos. Sin una seccion que las
  recoja se pierden, y con ella la division no es tal, son dos secciones nuevas.
- **Hardware no da de comer.** 7,2 candidatos por turno contra los 30 que pide
  el formato (7 destacadas + 25 titulares). Saldria medio vacia dos veces al
  dia, que es peor que no tenerla.

IA si da, pero **no con los feeds de tecnologia** (9,5 por turno). Da con feeds
de categoria, que es lo que se busco despues: simulando la seccion entera salen
**18 candidatos por turno de 10 medios, 3 de ellos espanoles**. De ahi que la
lista de `ia` en `medios.json` no sea la de tecnologia con un filtro: la mitad
son feeds de la seccion de IA del medio (TechCrunch, The Verge, Ars, y el de
Hipertextual, cuya ruta con `/categoria/` delante da 410).

Tres cosas que hay que saber para no romperla:

- **Los cupos de esta seccion son mas bajos** (6 destacadas en vez de 7, 15
  titulares de tope, 8 minimos por la manana), y viven en `CUPOS` dentro de
  `noticias.py`. Una seccion
  estrecha no es una seccion mal hecha: pedirle los 25 de tecnologia solo
  conseguiria que `validar` avisara en todas las ejecuciones. Ahi esta tambien
  la unica regla que cambia de rango: **no traer ninguna destacada de un medio
  espanol es aviso y no error**, porque los medios espanoles de IA dan 2
  candidatos por turno y habra turnos sin ninguno. Un ERROR que quien lo recibe
  no puede corregir solo ensena a saltarse los errores.
- **Tecnologia ya no publica IA**, y por eso su bloque `tema_ajeno` en
  `medios.json` apunta a la lista de `ia`. Se apunta, no se copia: dos listas
  iguales en dos sitios acaban distintas, y el dia que se desincronizan aparece
  una noticia que no entra en ninguna de las dos. Tecnologia se queda con 84
  candidatos por turno de los que 13 se van a IA, o sea que no se resiente.
- **El titular no basta para separarlas, tambien se mira de que feed vienen.**
  Los dos primeros turnos con IA abierta publicaron una noticia repetida en las
  dos secciones cada uno, las dos de TechCrunch: "Nvidia partners with data
  center developer Cloverleaf" y "Starcloud raises $250 million for orbital data
  centers". Ninguna decia en el titular una palabra de `propio` ("Nvidia" esta
  fuera a proposito y "data center" no esta), asi que `tema_ajeno` no podia
  cazarlas. Pero el propio medio ya las habia clasificado: estaban en su feed de
  IA. `enlaces_de_la_hermana()` descarta lo que el medio cuelga en el feed de la
  seccion hermana, que es `de_otra_seccion` aplicado a las hermanas: alli la
  categoria se lee en la URL y aqui en de que feed viene. Medido el 22-08-2026:
  de 8 noticias en los dos feeds a la vez, el titular cazaba 6 y escapaban esas
  2. Solo cuesta descargas en los medios con feed aparte para la hermana
  (Hipertextual, TechCrunch, The Verge y Ars Technica), y si ese feed no
  responde no se descarta nada suyo y se avisa: quedarse sin un medio entero por
  un fallo de red es peor que la repetida que esto evita.
- **La lista `propio` de IA son nombres propios y siglas**, no conceptos. Esta
  a proposito **sin "Nvidia"** (vende tarjetas graficas de juego), sin "chip" y
  sin "algoritmo": el filtro se aplico a las 680 publicadas y las 196 que se
  llevaba eran todas de IA, sin un solo falso positivo. Con "Nvidia" dentro,
  una noticia de graficas para jugar acabaria en la seccion de IA.

Como el filtro decide **de que va la noticia y no de quien viene**, se aplica a
todos los medios de tecnologia y no solo a los generalistas, al reves que
`filtrar_tema`. Un medio dedicado solo a IA no se pone en tecnologia.
