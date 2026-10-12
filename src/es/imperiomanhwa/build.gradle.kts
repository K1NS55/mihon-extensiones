import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    pkgName = "k1ns55.es.imperiomanhwa"
    name = "Imperio Manhwa"
    versionCode = 0
    contentWarning = ContentWarning.MIXED
    libVersion = "1.6"

    source {
        lang = "es"
        baseUrl = "https://imperiomanhwa.com"
    }

    deeplink {
        path("/manga/..*")
    }
}
