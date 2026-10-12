pluginManagement {
    includeBuild("gradle/build-logic")
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        maven(url = "https://www.jitpack.io")
    }
}

dependencyResolutionManagement {
    versionCatalogs {
        create("kei") { from(files("gradle/kei.versions.toml")) }
    }
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven(url = "https://www.jitpack.io")
    }
}

rootProject.name = "mihon-extensiones"
include(":core", ":compiler", ":lib:i18n")
val extensions = listOf(
    ":src:all:mangadex",
    ":src:es:olympusscanlation",
    ":src:es:manhwaweb",
    ":src:es:leercapitulo",
)
check(extensions.size <= 10) { "Este repositorio admite como máximo 10 extensiones" }
include(*extensions.toTypedArray())
