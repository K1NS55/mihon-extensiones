import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("publish", Path(__file__).parents[1] / "scripts/publish_index.py")
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class IndexTests(unittest.TestCase):
    """Fixtures prueban reglas del publicador, no la validez de un APK Android."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for module in publish.MODULES:
            build = self.root / "src" / module / "build"
            apk_dir = build / "outputs/apk/release"
            apk_dir.mkdir(parents=True)
            slug = module.replace("/", ".")
            (apk_dir / f"{slug}.apk").write_bytes(slug.encode())
            (build / "keiyoushi-source-info.json").write_text(json.dumps({
                "packageName": slug, "name": slug, "versionCode": 106001,
                "versionName": "1.6.1", "extensionLib": "1.6", "contentWarning": 1,
                "sources": [{"id": 9123456789012345678, "name": slug,
                             "lang": "es", "baseUrl": "https://example.org"}],
            }))
        icon = self.root / "core/src/main/res/mipmap-xhdpi/ic_launcher.png"
        icon.parent.mkdir(parents=True)
        icon.write_bytes(b"icon fixture")

    def tools(self, *args):
        slug = Path(args[-1]).stem
        if "apksigner" in args[0]:
            return "Number of signers: 1\nV2 Signer: certificate SHA-256 digest: " + "a" * 64
        return f"package: name='{slug}' versionCode='106001' versionName='1.6.1'"

    def generate(self):
        return publish.generate(self.root, self.root / "out", Path("tools"), "build-1")

    def test_generates_selected_entries_and_preserves_long_source_ids(self):
        with patch.object(publish, "run", side_effect=self.tools):
            result = self.generate()
        self.assertEqual(len(publish.MODULES), len(result["extensionList"]["extensions"]))
        self.assertEqual("9123456789012345678", result["extensionList"]["extensions"][0]["sources"][0]["id"])
        self.assertEqual(len(publish.MODULES), len(list((self.root / "out/apk").glob("*.apk"))))
        self.assertTrue((self.root / "out/repo.json").is_file())

    def test_rejects_debug_signature(self):
        with patch.object(publish, "run", return_value="CN=Android Debug"):
            with self.assertRaisesRegex(ValueError, "depuración"):
                self.generate()

    def test_supports_https_apk_hosting(self):
        with patch.object(publish, "run", side_effect=self.tools):
            index = publish.generate(self.root, self.root / "out", Path("tools"), "v1",
                                     apk_base_url="https://example.org/repo/apk")
        for entry in index["extensionList"]["extensions"]:
            self.assertTrue(entry["resources"]["apkUrl"].startswith("https://example.org/repo/apk/"))

    def test_rejects_missing_apk(self):
        next((self.root / "src").rglob("*.apk")).unlink()
        with patch.object(publish, "run", side_effect=self.tools):
            with self.assertRaisesRegex(ValueError, "exactamente un APK"):
                self.generate()

    def test_preserves_urls_for_identical_previously_published_apks(self):
        with patch.object(publish, "run", side_effect=self.tools):
            previous = self.generate()
            result = publish.generate(self.root, self.root / "next", Path("tools"), "build-2",
                                      previous=previous, previous_dir=self.root / "out")
        old_urls = [e["resources"]["apkUrl"] for e in previous["extensionList"]["extensions"]]
        new_urls = [e["resources"]["apkUrl"] for e in result["extensionList"]["extensions"]]
        self.assertEqual(old_urls, new_urls)

    def test_rejects_metadata_mismatch(self):
        def wrong(*args):
            return self.tools(*args).replace("106001", "106002")
        with patch.object(publish, "run", side_effect=wrong):
            with self.assertRaisesRegex(ValueError, "Metadatos"):
                self.generate()

    def test_rejects_mixed_signatures(self):
        def mixed(*args):
            value = self.tools(*args)
            return value.replace("a" * 64, "b" * 64) if "mangadex" in args[-1] else value
        with patch.object(publish, "run", side_effect=mixed):
            with self.assertRaisesRegex(ValueError, "misma firma"):
                self.generate()

    def test_rejects_changed_signer_and_non_incremented_version(self):
        entry = {"name": "Example", "packageName": "example", "versionCode": "106001"}
        previous = {"signingKey": "a", "extensionList": {"extensions": [entry]}}
        with self.assertRaisesRegex(ValueError, "firma cambió"):
            publish.check_version(entry, previous, "b")
        with self.assertRaisesRegex(ValueError, "Incrementa"):
            publish.check_version(entry, previous, "a")
        publish.check_version(entry, previous, "a", identical=True)
        publish.check_version(dict(entry, versionCode="106002"), previous, "a")


if __name__ == "__main__":
    unittest.main()
