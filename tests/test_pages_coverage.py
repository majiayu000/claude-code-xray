import hashlib
import json
import os
from pathlib import Path
import tempfile
import textwrap
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY / ".github/workflows/pages.yml"
GATE_CODE = textwrap.dedent(
    WORKFLOW.read_text().split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
)


class PagesCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / "site"
        self.site.mkdir()
        (self.root / "LICENSE").write_text("fixture license")
        for name in ["index.html", "about.html", "404.html", "sitemap.xml",
                     "robots.txt", "favicon.svg", "README.md", ".nojekyll",
                     ".xry-public-build"]:
            (self.site / name).write_text("fixture " + name)
        self.page = self.site / "page/explainer.html"
        self.page.parent.mkdir()
        self.page.write_text("fixture page")
        self.manifest = {
            "base_url": "https://majiayu000.github.io/claude-code-xray/",
            "publish_ready": True,
            "files": [{
                "path": "page/explainer.html",
                "sha256": hashlib.sha256(self.page.read_bytes()).hexdigest(),
            }],
        }
        self.write_manifest()
        self.write_checksums()

    def write_manifest(self):
        (self.site / "site-manifest.json").write_text(json.dumps(self.manifest))

    def write_checksums(self):
        lines = [
            hashlib.sha256(path.read_bytes()).hexdigest()
            + "  " + path.relative_to(self.site).as_posix() + "\n"
            for path in sorted(self.site.rglob("*")) if path.is_file()
        ]
        (self.root / "site.sha256").write_text("".join(lines))

    def run_gate(self, root=None):
        previous = Path.cwd()
        try:
            os.chdir(root or self.root)
            exec(compile(GATE_CODE, str(WORKFLOW), "exec"), {})
        finally:
            os.chdir(previous)

    def assert_blocked(self, message):
        with self.assertRaises(SystemExit) as result:
            self.run_gate()
        self.assertTrue(str(result.exception).startswith("Publication blocked: "))
        self.assertIn(message, str(result.exception))

    def test_current_site_passes(self):
        self.run_gate(REPOSITORY)

    def test_complete_fixture_passes(self):
        self.run_gate()

    def test_every_deployed_file_digest_is_checked(self):
        for path in sorted(self.site.rglob("*")):
            if not path.is_file():
                continue
            with self.subTest(path=path.relative_to(self.site).as_posix()):
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                try:
                    self.assert_blocked("sha256 mismatch")
                finally:
                    path.write_bytes(original)

    def test_unexpected_root_and_nested_files_are_blocked(self):
        for rel in ["evil.html", "assets/extra.css", ".unexpected"]:
            with self.subTest(path=rel):
                path = self.site / rel
                path.parent.mkdir(exist_ok=True)
                path.write_text("unexpected fixture")
                try:
                    self.assert_blocked("files missing from site.sha256: " + rel)
                finally:
                    path.unlink()

    def test_missing_deployed_file_is_blocked(self):
        (self.site / "index.html").unlink()
        self.assert_blocked("site.sha256 paths missing on disk: index.html")

    def test_missing_checksum_entry_is_blocked(self):
        checksums = self.root / "site.sha256"
        checksums.write_text("\n".join(
            line for line in checksums.read_text().splitlines()
            if not line.endswith("  site-manifest.json")
        ) + "\n")
        self.assert_blocked("files missing from site.sha256: site-manifest.json")

    def test_non_explainer_manifest_entry_passes(self):
        self.manifest["files"].append({
            "path": "index.html",
            "sha256": hashlib.sha256((self.site / "index.html").read_bytes()).hexdigest(),
        })
        self.write_manifest()
        self.write_checksums()
        self.run_gate()

    def test_wrong_base_url_is_blocked_even_with_updated_checksums(self):
        for url in ["https://majiayu000.github.io/wrong-path/",
                    "https://majiayu000.github.io/claude-code-xray",
                    "https://majiayu000.github.io/claude-code-xray/?query=1",
                    "https://majiayu000.github.io/claude-code-xray/#fragment",
                    "https://majiayu000.github.io:443/claude-code-xray/",
                    "https://user@majiayu000.github.io/claude-code-xray/",
                    "http://majiayu000.github.io/claude-code-xray/",
                    "https://example.invalid/claude-code-xray/"]:
            with self.subTest(url=url):
                self.manifest["base_url"] = url
                self.write_manifest()
                self.write_checksums()
                self.assert_blocked("exact URL https://majiayu000.github.io/claude-code-xray/")

    def test_duplicate_checksum_path_is_blocked(self):
        checksums = self.root / "site.sha256"
        lines = checksums.read_text().splitlines(keepends=True)
        checksums.write_text("".join(lines + [lines[0]]))
        self.assert_blocked("duplicate path in site.sha256")

    def test_checksum_path_outside_site_is_not_read(self):
        (self.root / "outside.txt").write_text("external fixture")
        checksums = self.root / "site.sha256"
        checksums.write_text(checksums.read_text() + "0" * 64 + "  ../outside.txt\n")
        self.assert_blocked("site.sha256 paths missing on disk: ../outside.txt")

    def test_missing_checksum_file_fails(self):
        (self.root / "site.sha256").unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_gate()

    def test_explainer_digest_contract_is_preserved(self):
        self.manifest["files"][0]["sha256"] = "bad"
        self.write_manifest()
        self.write_checksums()
        self.assert_blocked("page/explainer.html: sha256 mismatch")

    def test_unlisted_explainer_contract_is_preserved(self):
        self.manifest["files"] = []
        self.write_manifest()
        self.write_checksums()
        self.assert_blocked("explainer.html files missing from manifest")

    def test_publish_ready_contract_is_preserved(self):
        self.manifest["publish_ready"] = False
        self.write_manifest()
        self.write_checksums()
        self.assert_blocked("site manifest is not marked publish_ready")

    def test_license_contract_is_preserved(self):
        (self.root / "LICENSE").unlink()
        self.assert_blocked("a regular LICENSE file is required")


if __name__ == "__main__":
    unittest.main()
