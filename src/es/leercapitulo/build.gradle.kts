import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    pkgName = "k1ns55.es.leercapitulo"
    name = "LeerCapitulo"
    versionCode = 0
    contentWarning = ContentWarning.SAFE
    libVersion = "1.6"

    source {
        lang = "es"
        baseUrl = "https://www.leercapitulo.co"
    }

    deeplink {
        path("/manga/..*")
    }
}
