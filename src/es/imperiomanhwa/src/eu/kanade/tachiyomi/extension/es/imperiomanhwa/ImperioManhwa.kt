package eu.kanade.tachiyomi.extension.es.imperiomanhwa

import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.model.SMangaUpdate
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.network.rateLimit
import keiyoushi.source.KeiSource
import keiyoushi.utils.asJsoup
import keiyoushi.utils.runWebView
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Headers
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import java.time.OffsetDateTime
import kotlin.time.Duration.Companion.seconds

@Source
abstract class ImperioManhwa : KeiSource() {
    private val readerMutex = Mutex()

    override fun OkHttpClient.Builder.configureClient() = rateLimit(1, 2.seconds)

    override fun Headers.Builder.configureHeaders(): Headers.Builder = set("Referer", "$baseUrl/")

    private suspend fun props(url: String): JsonObject {
        val doc = client.get(url).asJsoup()
        val data = doc.selectFirst("script[data-page]")?.data()
            ?: doc.selectFirst("[data-page]")?.attr("data-page")
            ?: error("Abre la fuente en WebView y comprueba el acceso al sitio")
        return Json.parseToJsonElement(data).jsonObject.getValue("props").jsonObject
    }

    private fun JsonObject.text(key: String): String? = get(key)?.jsonPrimitive?.contentOrNull
    private fun JsonObject.array(key: String): JsonArray = get(key)?.jsonArray ?: JsonArray(emptyList())

    private fun JsonObject.manga() = SManga.create().apply {
        setUrlWithoutDomain(baseUrl.toHttpUrl().resolve(getValue("url").jsonPrimitive.content)!!.toString())
        title = getValue("title").jsonPrimitive.content
        thumbnail_url = text("cover_lg") ?: text("cover")
        description = text("synopsis")
        author = array("authors").joinToString { it.jsonObject.text("name").orEmpty() }.ifEmpty { null }
        artist = array("artists").joinToString { it.jsonObject.text("name").orEmpty() }.ifEmpty { null }
        genre = array("genres").joinToString { it.jsonObject.text("name").orEmpty() }
        status = when (text("status")) {
            "ongoing" -> SManga.ONGOING
            "completed" -> SManga.COMPLETED
            "hiatus" -> SManga.ON_HIATUS
            "cancelled" -> SManga.CANCELLED
            else -> SManga.UNKNOWN
        }
    }

    private suspend fun catalog(url: String): MangasPage {
        val data = props(url)
        val pagination = data["pagination"]?.jsonObject
        return MangasPage(data.getValue("series").jsonArray.map { it.jsonObject.manga() }, pagination?.text("next") != null)
    }

    private fun paged(path: String, page: Int) = "$baseUrl/$path/" + if (page > 1) "page/$page/" else ""

    override suspend fun getPopularManga(page: Int) = catalog(paged("mejores-manhwas-2026", page))

    override suspend fun getLatestUpdates(page: Int) = catalog(paged("manga", page))

    override suspend fun getSearchMangaList(page: Int, query: String, filters: FilterList): MangasPage {
        if (query.isBlank()) return getLatestUpdates(page)
        return catalog(
            "$baseUrl/buscar".toHttpUrl().newBuilder()
                .addQueryParameter("q", query)
                .addQueryParameter("page", page.toString()).build().toString(),
        )
    }

    override suspend fun getMangaByUrl(url: HttpUrl): SManga? {
        if (url.host != baseUrl.toHttpUrl().host || !Regex("/manga/[^/]+/").matches(url.encodedPath)) return null
        return props(url.toString()).getValue("series").jsonObject.manga()
    }

    override suspend fun fetchMangaUpdate(manga: SManga, chapters: List<SChapter>, fetchDetails: Boolean, fetchChapters: Boolean): SMangaUpdate {
        val data = props(baseUrl + manga.url)
        val result = mutableListOf<SChapter>()
        if (fetchChapters) {
            val last = data.getValue("chapters_pagination").jsonObject.getValue("last").jsonPrimitive.int
            result += data.getValue("chapters").jsonArray.map { it.jsonObject.chapter() }
            for (page in 2..last) {
                val items = client.get(baseUrl + manga.url.trimEnd('/') + "/capitulos/$page.json").use {
                    Json.parseToJsonElement(it.body.string()).jsonObject.getValue("items").jsonArray
                }
                result += items.map { it.jsonObject.chapter() }
            }
        }
        return SMangaUpdate(if (fetchDetails) data.getValue("series").jsonObject.manga() else manga, if (fetchChapters) result else chapters)
    }

    private fun JsonObject.chapter() = SChapter.create().apply {
        setUrlWithoutDomain(baseUrl.toHttpUrl().resolve(getValue("url").jsonPrimitive.content)!!.toString())
        name = getValue("label").jsonPrimitive.content
        if (get("locked")?.jsonPrimitive?.booleanOrNull == true) name += " [Restringido]"
        chapter_number = text("number")?.toFloatOrNull() ?: -1f
        date_upload = runCatching { OffsetDateTime.parse(text("published_at")).toInstant().toEpochMilli() }.getOrDefault(0L)
    }

    override suspend fun getPageList(chapter: SChapter): List<Page> = readerMutex.withLock {
        // Let the site's own reader resolve its image manifest; do not return the
        // single preview image from the initial HTML as a complete chapter.
        runWebView<List<Page>>(timeout = 60.seconds) {
            javaScriptEnabled = true
            domStorageEnabled = true
            blockImages = true
            poll(1.seconds) {
                evaluateJs(READER_SCRIPT) { value ->
                    if (value != "null") {
                        val data = Json.parseToJsonElement(value).jsonObject
                        data.text("error")?.let { error(it) }
                        val urls = data.getValue("urls").jsonArray
                        resolve(urls.mapIndexed { index, url -> Page(index, imageUrl = url.jsonPrimitive.content) })
                    }
                }
            }
            loadUrl(baseUrl + chapter.url, headers.toMap())
        }
    }

    companion object {
        // Also exercised by scripts/smoke_imperiomanhwa.py in Chromium.
        val READER_SCRIPT = """
            (() => {
                const node = document.querySelector('script[data-page]');
                if (!node) return null;
                const page = JSON.parse(node.textContent);
                if (page.component !== 'Reader/Chapter') return null;
                const props = page.props;
                if (props.chapter.locked) return {error: 'Capítulo restringido: comprueba el acceso en WebView'};
                const images = Array.from(document.querySelectorAll('main.reader-pages img'));
                if (!props.total || images.length !== props.total) return null;
                const urls = images.map(img => {
                    const candidates = (img.getAttribute('srcset') || '').split(',').map(s => s.trim()).filter(Boolean);
                    return candidates.length ? candidates[candidates.length - 1].split(/\s+/)[0] : img.src;
                });
                if (!urls.every(url => /^https?:\/\//.test(url))) return null;
                return {urls};
            })()
        """.trimIndent()
    }
}
