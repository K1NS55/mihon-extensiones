# Extensiones personales para Mihon

Repositorio de **K1NS55**, limitado a un máximo de diez extensiones. Incluye únicamente:

| Extensión | Sitio | Idiomas |
| --- | --- | --- |
| Olympus Scanlation | https://olympusxyz.com/ | Español |
| MangaDex | https://mangadex.org/ | Multilingüe, incluidos español y español latinoamericano |
| ManhwaWeb | https://manhwaweb.com/ | Español; versiones de los grupos disponibles |
| LeerCapitulo | https://www.leercapitulo.co/ | Español |
| Imperio Manhwa | https://imperiomanhwa.com/ | Español |

Las primeras cuatro fuentes usan código adaptado de [Keiyoushi](https://github.com/keiyoushi/extensions-source),
commit `53a6f21bb143649751632667cafa0eff413ae487`, con licencia Apache-2.0.
Imperio Manhwa es una integración propia basada en el sitio actual; utiliza Android WebView
para cargar todas las imágenes del lector. Mantén Android System WebView actualizado.
Los capítulos restringidos por el sitio requieren el acceso correspondiente.
Consulta [NOTICE](NOTICE) y [LICENSE](LICENSE). No es un repositorio oficial de Mihon ni de los sitios.

## Instalar en Mihon

Requiere **Mihon 0.21.0 o posterior con soporte de extensiones API 1.6**.
La versión estable 0.21.0 admite las API 1.4 y 1.6; se comprobó en su código etiquetado.
En Ajustes → Explorar → repositorios/tiendas de extensiones, agrega:

```text
https://raw.githubusercontent.com/K1NS55/mihon-extensiones/repo/index.json
```

Los APK se publican en [GitHub Releases](https://github.com/K1NS55/mihon-extensiones/releases).
Después de añadir el repositorio, instala las fuentes desde la lista de extensiones.
Las instalaciones requieren la autorización habitual de Android y, cuando Mihon lo solicite,
confirmar la confianza en la extensión.

Huella SHA-256 del certificado de publicación:

```text
a1cfdced847c7c2ed8699186337b5d36ad9afd4036e57ca72f385066f7332fde
```

Los paquetes usan el prefijo `eu.kanade.tachiyomi.extension.k1ns55` para no reemplazar
los APK firmados por Keiyoushi. Los identificadores de fuente se conservan; si ya instalaste
la misma fuente desde otro repositorio, evita mantener ambas extensiones activas.
La lectura sin conexión utiliza las descargas nativas de Mihon.

## Estado de verificación

Consulta [docs/VALIDACION.md](docs/VALIDACION.md) para los resultados reales y limitaciones.
Una compilación correcta o un sondeo HTTP no demuestra por sí solo que el APK funcione en el teléfono.

## Desarrollo en Cloud

No requiere Android Studio. El proyecto usa Java 25, Gradle 9.8.1, Kotlin 2.4.10,
Android Gradle Plugin 9.4.1, SDK 37 y Android 8.0/API 26 como mínimo.
Las versiones están fijadas en `gradle/`; el wrapper verifica el SHA-256 de Gradle.

```bash
cd /workspace/mihon-extensiones
bash scripts/setup-cloud.sh
source /workspace/toolchains/activate.sh
bash scripts/build.sh
./gradlew --no-daemon --max-workers=4 :core:testDebugUnitTest :core:lintRelease :lib:i18n:lintRelease
python3 -m unittest discover -s tests -v
/workspace/.venvs/mihon-smoke/bin/python scripts/smoke_sources.py
/workspace/.venvs/mihon-smoke/bin/python scripts/smoke_html_sources.py leercapitulo
```

Para recompilar solamente una extensión modificada:

```bash
bash scripts/build.sh :src:es:olympusscanlation
```

El script de preparación es específico del entorno Cloud Linux x86_64 y conserva cachés
en `/workspace`. Las tareas Cloud ya están aisladas: utiliza el checkout existente;
no crees un worktree salvo que se solicite. No hay servidores locales que iniciar.
El formateo se comprueba durante la compilación; no se reescriben fuentes automáticamente.

## Publicaciones y actualizaciones

GitHub Actions valida las extensiones seleccionadas, ejecuta pruebas y lint, y publica en cada push
a `main` que cambie código o configuración, o ejecución manual del workflow. Las cachés de Gradle reutilizan las tareas sin cambios.
Las pull requests solo validan; no reciben la clave de firma.

Para modificar una fuente, cambia su código y aumenta `versionCode` en el `build.gradle.kts`
de ese módulo. Conserva siempre la clave de firma. El publicador rechaza una firma distinta,
una versión inferior, y un APK cambiado con el mismo código de versión. Un APK idéntico puede
republicarse sin incrementar la versión. No elimines las publicaciones antiguas cuyos APK
sigan referenciados por un índice.

La rama `main` contiene el código. La rama `repo` contiene `index.json` en el formato actual de
Mihon, `repo.json`, el índice heredado `index.min.json`, iconos y APK. Cada GitHub Release
conserva APK e índices y un archivo `SHA256SUMS`. Mihon consulta el índice permanente y ofrece
las actualizaciones cuando aumenta la versión de una extensión.

### Firma de GitHub Actions

Se necesitan dos secretos del repositorio, en Settings → Secrets and variables → Actions:

| Secreto | Contenido |
| --- | --- |
| `SIGNING_KEY` | Keystore JKS codificado en base64 |
| `KEY_STORE_PASSWORD` | Contraseña del keystore y de la clave |

El alias fijo es `mihon`. No se necesita un PAT para publicar desde Actions: se usa el
`GITHUB_TOKEN` del workflow con permiso `contents: write`.
La primera clave se generó fuera del repositorio en el entorno Cloud y debe conservarse
privadamente. **No generes otra para actualizaciones de estos APK.**
`scripts/create-signing-key.sh` es únicamente para iniciar otro repositorio o una identidad nueva;
nunca crea ni reemplaza una clave automáticamente durante CI.

## Fuentes y acceso

Se utilizan los endpoints públicos implementados por Keiyoushi, con sus filtros y límites
de solicitudes. No se añade un sistema de descargas separado, evasión de autenticación,
DRM ni acceso a capítulos privados. Un capítulo retirado o no disponible puede devolver 404.
Los sitios y sus CDN pueden cambiar o requerir interacción legítima en el navegador de Mihon.

El sondeo HTTP toma una obra y un capítulo de muestra por sitio, comprueba sus URLs de imágenes
y solicita una muestra de la primera imagen. No descarga capítulos completos y no ejecuta el APK.
Los informes distinguen las comprobaciones que pasaron de las que quedaron bloqueadas.

Para añadir otra fuente solicitada, importa solo su módulo y dependencias, actualiza
`settings.gradle.kts`, `scripts/build.sh` y `scripts/publish_index.py`, y conserva el límite de diez.
