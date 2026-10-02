import hashlib
import json
import os
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import patch


REPOSITORY = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY / ".github/workflows/pages.yml"
GATE_CODE = textwrap.dedent(
    WORKFLOW.read_text().split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
)


class PagesGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / "site"
        self.site.mkdir()
        (self.root / "LICENSE").write_text("fixture license")
        self.outside = self.root / "outside"
        self.outside.mkdir()
        self.external_file = self.outside / "explainer.html"
        self.external_file.write_text("safe fixture bytes")
        self.manifest = {
            "base_url": "https://majiayu000.github.io/claude-code-xray/",
            "publish_ready": True,
            "files": [],
        }
        self.write_manifest()

    def write_manifest(self):
        (self.site / "site-manifest.json").write_text(json.dumps(self.manifest))
        lines = [
            hashlib.sha256(path.read_bytes()).hexdigest()
            + "  " + path.relative_to(self.site).as_posix() + "\n"
            for path in sorted(self.site.rglob("*"))
            if path.is_file() and not path.is_symlink()
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

    def test_regular_files_pass(self):
        (self.site / "index.html").write_text("fixture home")
        (self.site / ".nojekyll").touch()
        page = self.site / "page/explainer.html"
        page.parent.mkdir()
        page.write_text("fixture page")
        self.manifest["files"] = [{
            "path": "page/explainer.html",
            "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
        }]
        self.write_manifest()
        self.run_gate()

    def test_unlisted_explainer_symlink_is_blocked(self):
        link = self.site / "extra/explainer.html"
        link.parent.mkdir()
        link.symlink_to(self.external_file)
        self.assert_blocked("extra/explainer.html")

    def test_asset_symlink_is_blocked(self):
        (self.site / "asset.txt").symlink_to(self.external_file)
        self.assert_blocked("asset.txt")

    def test_directory_symlink_is_blocked(self):
        (self.site / "linked").symlink_to(self.outside, target_is_directory=True)
        self.assert_blocked("linked")

    def test_intermediate_symlink_is_blocked_before_read(self):
        directory = self.site / "nested"
        directory.mkdir()
        (directory / "linked").symlink_to(self.outside, target_is_directory=True)
        self.manifest["files"] = [{
            "path": "nested/linked/explainer.html", "sha256": "fixture",
        }]
        self.write_manifest()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unsafe read")):
            self.assert_blocked("nested/linked")

    def test_internal_symlink_is_blocked(self):
        target = self.site / "asset.txt"
        target.write_text("fixture asset")
        (self.site / "linked.txt").symlink_to(target)
        self.assert_blocked("linked.txt")

    def test_dangling_symlink_is_blocked(self):
        (self.site / "dangling").symlink_to(self.outside / "missing")
        self.assert_blocked("dangling")

    def test_site_root_symlink_is_blocked(self):
        self.site.rename(self.root / "original_site")
        self.site.symlink_to(self.root / "original_site", target_is_directory=True)
        self.assert_blocked("site")

    def test_manifest_symlink_is_blocked_before_read(self):
        (self.site / "site-manifest.json").unlink()
        (self.site / "site-manifest.json").symlink_to(self.external_file)
        with patch.object(Path, "read_text", side_effect=AssertionError("unsafe read")):
            self.assert_blocked("site-manifest.json")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO requires POSIX")
    def test_special_file_is_blocked(self):
        os.mkfifo(self.site / "pipe")
        self.assert_blocked("pipe")

    def test_escaping_manifest_paths_are_blocked_before_read(self):
        read_bytes = Path.read_bytes

        def read_inside_site(path):
            self.assertTrue(path.resolve().is_relative_to(self.site.resolve()),
                            "unsafe read outside site")
            return read_bytes(path)

        for rel in [str(self.external_file), "../outside/explainer.html",
                    "page/../../outside/explainer.html"]:
            with self.subTest(path=rel):
                self.manifest["files"] = [{"path": rel, "sha256": "fixture"}]
                self.write_manifest()
                with patch.object(Path, "read_bytes", read_inside_site):
                    self.assert_blocked("path must stay inside site/")

    def test_walk_errors_propagate(self):
        with patch.object(os, "scandir", side_effect=PermissionError("fixture walk failure")):
            with self.assertRaisesRegex(PermissionError, "fixture walk failure"):
                self.run_gate()

    def test_digest_mismatch_still_blocks(self):
        page = self.site / "page/explainer.html"
        page.parent.mkdir()
        page.write_text("fixture page")
        self.manifest["files"] = [{"path": "page/explainer.html", "sha256": "bad"}]
        self.write_manifest()
        self.assert_blocked("sha256 mismatch")

    def test_unlisted_regular_explainer_still_blocks(self):
        page = self.site / "page/explainer.html"
        page.parent.mkdir()
        page.write_text("fixture page")
        self.assert_blocked("explainer.html files missing from manifest")

    def test_unapproved_host_still_blocks(self):
        self.manifest["base_url"] = "https://example.invalid/"
        self.write_manifest()
        self.assert_blocked("base_url must be an HTTPS URL on majiayu000.github.io")


if __name__ == "__main__":
    unittest.main()
