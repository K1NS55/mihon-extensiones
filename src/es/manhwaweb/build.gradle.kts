import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    pkgName = "k1ns55.es.manhwaweb"
    name = "ManhwaWeb"
    versionCode = 13
    contentWarning = ContentWarning.MIXED
    libVersion = "1.6"

    source {
        lang = "es"
        baseUrl = "https://manhwaweb.com"
    }

    deeplink {
        path("/manhwa/..*")
    }
}
