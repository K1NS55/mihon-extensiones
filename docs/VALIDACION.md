# Validación del entorno y la primera compilación

Resultados medidos en Cloud, con Java 25.0.4.1, Gradle 9.8.1 y SDK 37.
El formato del índice y la API 1.6 se contrastaron con Mihon estable **v0.21.0**.

## Compilación y pruebas

- Los tres módulos completaron `assembleRelease` y `lintRelease`.
- `core:testDebugUnitTest`: **6 pruebas ejecutadas, 0 fallos, 0 omitidas**.
- Publicador Python: **7 pruebas ejecutadas, 0 fallos**. Son pruebas de las reglas de
  publicación con fixtures; no sustituyen la comprobación real de APK.
- Los APK de publicación se compilaron con la misma clave RSA de 4096 bits.
- El publicador ejecuta `apksigner verify --verbose --print-certs` y `aapt dump badging`
  sobre cada APK real; exige que certificado, paquete y versión coincidan con el índice.
- Lint de las tres extensiones y las bibliotecas compartidas: **0 errores**.
  Quedan 15 advertencias heredadas: 10 en core, 2 en MangaDex, 2 en ManhwaWeb y 1 en Olympus.
- `scripts/setup-cloud.sh` se ejecutó correctamente sobre la instalación existente;
  reutilizó las herramientas y cachés sin modificar fuentes.

## Sondeos HTTP públicos

| Fuente | Búsqueda, populares, últimas actualizaciones | Ficha y capítulos | URLs de imágenes |
| --- | --- | --- | --- |
| Olympus | Verificados en una muestra | Verificados; primera página de capítulos | 43 URLs extraídas |
| MangaDex | Verificados en español | Verificados en una muestra | 26 URLs extraídas |
| ManhwaWeb | Verificados | Verificados en una muestra | 16 URLs extraídas |

Tras habilitar los dominios de los CDN y enviar las cabeceras `Referer`/`Origin` que
utiliza `KeiSource`, **MangaDex y ManhwaWeb devolvieron la primera imagen de la muestra**
con un tipo de contenido de imagen válido. Olympus devolvió HTTP 403 con el título
`Attention Required! | Cloudflare` en su servidor de imágenes. No se intentó eludir ese bloqueo;
la lectura completa de Olympus no queda verificada. La primera ronda también encontró
bloqueos de política de red del entorno; esos resultados se distinguieron del bloqueo
HTTP de Cloudflare confirmado en la última comprobación.

Tres capítulos recientes de MangaDex devolvieron **404** en `/at-home/server` pese a aparecer
en el catálogo. Otra muestra de 26 páginas sí devolvió el servidor y sus URLs. Los capítulos
no disponibles no se presentan como comprobaciones exitosas ni se intenta sortear la restricción.

`scripts/smoke_sources.py` guarda las comprobaciones y observaciones por fuente en
`reports/source-smoke.json`. Si falla una comprobación, termina con estado distinto de cero.
No ejecuta las clases Kotlin ni la aplicación Android, no verifica todos los capítulos y
no descarga todas las imágenes. Los sitios pueden cambiar después de esta comprobación.

## Prueba pendiente en un teléfono

Para cada extensión: instalar desde el repositorio, buscar una obra, abrir su ficha,
revisar el orden de capítulos, leer un capítulo completo, descargarlo con Mihon, activar
modo avión y comprobar su lectura. También queda por verificar una actualización instalada
sobre una versión anterior con la misma firma. No se declara que estas pruebas ya hayan pasado.

## Firma y automatización

La integración de GitHub permitió leer el repositorio y confirmó permisos de escritura,
pero la API de secretos devolvió `403 Resource not accessible by integration`.
Se solicitó ampliar el permiso de Secrets. Mientras no se almacenen `SIGNING_KEY` y
`KEY_STORE_PASSWORD` en Actions, las publicaciones automáticas firmadas no pueden completarse.
La clave inicial permanece privada fuera del checkout y no forma parte del código ni de los APK.

## Distribución publicada

La versión [v1.0.0](https://github.com/K1NS55/mihon-extensiones/releases/tag/v1.0.0)
está publicada. Sus enlaces descargan los APK desde una revisión inmutable de la rama
de distribución. Se descargaron los tres archivos sin autenticación y se comprobaron
sus hashes SHA-256 y firmas. El índice público se contrastó con el índice local y se
validó también contra el esquema Protobuf de índices de Keiyoushi/Mihon.

La credencial Cloud rechazó la subida de adjuntos a `uploads.github.com` con 401;
por eso la primera release enlaza APK alojados en Git. La instalación desde Mihon
utiliza las URLs absolutas del índice y no depende de adjuntos de Releases.

El primer workflow de GitHub Actions falló porque el runner no traía `sdkmanager`.
Se añadió un instalador explícito con versión y SHA-256 fijados. El resultado de
los workflows remotos se puede consultar en la pestaña Actions; las pruebas locales
anteriores no se presentan como ejecuciones exitosas de CI.

El último informe HTTP de esta sesión se conserva en [HTTP_RESULT.json](HTTP_RESULT.json).

## Ejecuciones remotas y repetibilidad

La ejecución [38197011137](https://github.com/K1NS55/mihon-extensiones/actions/runs/38197011137)
completó correctamente el trabajo `verify`: compilación y lint de los tres APK, pruebas del
publicador, pruebas y lint de las bibliotecas compartidas. El trabajo `publish` falló
exclusivamente en `Cargar clave privada`: `SIGNING_KEY` y `KEY_STORE_PASSWORD` no están
configurados. La API para administrar los secretos continúa respondiendo 403 a la integración.

La recompilación local firmada reutilizó 241 de 248 tareas. El publicador aceptó los tres
APK contra el índice de v1.0.0 sin cambiar las versiones: conservan exactamente los mismos
bytes y certificados. No se han cambiado ni sustituido los APK publicados.

El workflow ahora comprueba los secretos antes de instalar herramientas para publicar,
ignora cambios exclusivamente documentales y detiene la publicación si no puede consultar
el índice anterior. La subida de la rama `repo` se probó usando el checkout autenticado y
un índice Git temporal, sin modificar los archivos ni el índice de trabajo de `main`.

## Confirmación posterior en Mihon por el propietario

El usuario confirmó que Olympus, MangaDex y ManhwaWeb cargan correctamente en su
aplicación y permiten descargar capítulos. Esta es una prueba en el dispositivo
informada por el usuario; los resultados y bloqueos de los sondeos Cloud anteriores
se conservan como evidencia de aquel entorno, no como un fallo confirmado en su teléfono.

## Incorporación de Leer Capítulo

Se incorporó la implementación mantenida de Keiyoushi para `https://www.leercapitulo.co`,
con paquete personal `eu.kanade.tachiyomi.extension.k1ns55.es.leercapitulo` y API 1.6.
La compilación `assembleRelease` y `lintRelease` terminaron correctamente. El APK se
firmó con el certificado original del repositorio, sin regenerar la clave.

La muestra HTTP confirmó populares, actualizaciones, búsqueda por título, ficha,
390 capítulos y 7 URLs de imágenes; la primera imagen respondió con contenido de imagen.
Informe: [HTTP_LEERCAPITULO.json](HTTP_LEERCAPITULO.json). La prueba de esta nueva
extensión dentro de Mihon queda pendiente de confirmación del usuario.

Las 8 pruebas del publicador pasaron. Se añadió una comprobación que conserva las
URLs de APK ya publicados cuando sus bytes y versión permanecen idénticos.
Olympus, MangaDex y ManhwaWeb mantienen sus APK, versiones, firma y enlaces previos.

## Incorporación de Imperio Manhwa

El usuario confirmó `https://imperiomanhwa.com/` y activó el acceso de red.
Se implementó una fuente propia con catálogo, populares, búsqueda, ficha y todos
los capítulos paginados. El lector inicial solo contiene una imagen: Android
WebView ejecuta el JavaScript del sitio y espera a tener las URLs de todas las
imágenes indicadas por `total`, evitando publicar capítulos incompletos.
Los capítulos restringidos muestran un error de acceso; no se modifica la
protección del sitio. La carga del lector se serializa y tiene un límite de 60 segundos.

`assembleRelease` y `lintRelease` pasaron; se usó la misma clave del repositorio.
El sondeo reproducible es `scripts/smoke_imperiomanhwa.py`; necesita Chromium,
Playwright 1.62.0 y las dependencias de `scripts/requirements-smoke.txt`.
En este entorno se ejecuta con:

```sh
PYTHONPATH=/workspace/.venvs/mihon-smoke/lib/python3.12/site-packages python3 scripts/smoke_imperiomanhwa.py
```

El sondeo ejecuta exactamente el selector JavaScript incluido en la fuente dentro
de Chromium. Las peticiones pasan por curl, que valida TLS con los certificados
del sistema; no se desactiva la verificación TLS. Esta comprobación no sustituye
una prueba del APK en Mihon/Android WebView en el teléfono.

Resultado: catálogo y populares con dos páginas, búsqueda, ficha y 100 capítulos
sin duplicados; lector con 10 imágenes y descarga verificada de las imágenes 1, 2
y 10. Informe: [HTTP_IMPERIOMANHWA.json](HTTP_IMPERIOMANHWA.json).
Las 8 pruebas del publicador también pasaron. Los cuatro APK anteriores conservan
sus versiones, bytes, firma y URLs de descarga.

## Actualización de ManhwaWeb 1.6.14

El sitio migró su API a `https://api.manhwaweb.com` y cambió el esquema:
los créditos usan `autor`/`artista` y los capítulos contienen `versions` con los
enlaces, fechas y grupos. La fuente anterior consultaba Railway y esperaba
`_extras` y `create` en el capítulo, campos que ya no existen.
Se adaptó la implementación mantenida de Keiyoushi conservando paquete, ID de
fuente y firma. Se incluyen las versiones publicadas de cada capítulo y se
omiten las que todavía no tienen fecha. No requiere migrar la biblioteca.

Sondeo real: populares, actualizaciones, búsqueda, ficha, versiones de capítulos,
34 URLs de imágenes y descarga de la primera imagen correctos.
Evidencia: [HTTP_MANHWAWEB_UPDATE.json](HTTP_MANHWAWEB_UPDATE.json).

Compilación y lint correctos; 8 pruebas del publicador pasaron. APK 1.6.14 firmado
con la clave original, mismo ID de fuente y paquete; las otras cuatro entradas
del índice y sus APK se conservan. Pendiente probar la actualización en el teléfono.

## Actualización de Olympus Scanlation 1.6.1

La lista de capítulos aún usaba el subdominio `panel`, que devuelve HTTP 520,
aunque el catálogo público funciona. Ahora se consulta `/api/series/{slug}/chapters`
en el dominio activo. Las imágenes se obtienen del lector HTML con el selector
`main.strip div.panel > img`, como hace la implementación mantenida de Keiyoushi,
en lugar del antiguo endpoint de páginas. Se conserva la búsqueda automática
del dominio y la limitación de peticiones. Una página vacía inesperada interrumpe
la actualización con error en lugar de repetir peticiones indefinidamente.

Caso informado por el usuario: **El Chetado (Overgeared)**, ID 178.
Se comprobaron ficha, búsqueda, 345 registros de capítulos en 9 páginas sin
duplicados, último capítulo 343 y sus 35 URLs de imágenes. El dominio activo
obtenido desde `olympus.pages.dev` era `olympusbiblioteca.com`; el dominio anterior
también respondió a las rutas públicas. El CDN devolvió HTTP 403 desde Cloud,
incluso con Referer y Origin: la descarga de imágenes necesita prueba en teléfono.
Informe: [HTTP_OLYMPUS_UPDATE.json](HTTP_OLYMPUS_UPDATE.json).

Compilación y lint correctos; 8 pruebas del publicador pasaron. Se mantienen
paquete, ID de fuente, IDs de obras/capítulos y certificado. No requiere migrar
la biblioteca. Las otras cuatro extensiones conservan sus APK y versiones.
