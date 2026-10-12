import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    pkgName = "k1ns55.es.olympusscanlation"
    name = "Olympus Scanlation"
    versionCode = 0
    contentWarning = ContentWarning.SAFE
    libVersion = "1.6"

    source {
        lang = "es"
        baseUrl {
            custom("https://olympusxyz.com")
        }
        versionId = 3
    }
}
