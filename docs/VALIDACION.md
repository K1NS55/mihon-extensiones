# Validación del entorno y la primera compilación

Resultados medidos en Cloud, con Java 25.0.4.1, Gradle 9.8.1 y SDK 37.
El formato del índice y la API 1.6 se contrastaron con Mihon estable **v0.21.0**.

## Compilación y pruebas

- Los tres módulos completaron `assembleRelease` y `lintRelease`.
- `core:testDebugUnitTest`: **6 pruebas ejecutadas, 0 fallos, 0 omitidas**.
- Publicador Python: **6 pruebas ejecutadas, 0 fallos**. Son pruebas de las reglas de
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

La descarga de la primera imagen de cada muestra fue bloqueada por la política de red
del entorno Cloud (`CONNECT 403`) al acceder a sus CDN. Los dominios necesarios se guardaron
en la configuración del entorno. Esto no demuestra que los sitios rechacen la conexión desde
Mihon: el rechazo ocurrió en el proxy del entorno, antes de llegar al servidor.

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
