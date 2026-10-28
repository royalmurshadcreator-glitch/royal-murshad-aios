"""Safe path validation tests using temporary directories only."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aios_path_security import resolve_app_save_path


class AppSavePathTests(unittest.TestCase):
    def test_app_slug_resolves_to_direct_child(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = resolve_app_save_path(root, "royal-finance_2")
            self.assertEqual(target, root.resolve() / "royal-finance_2.json")

    def test_invalid_app_slugs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for slug in ["", ".", "..", "../secret", "..\\secret", "a/b", "a\\b", "x:y", "name.json", "a" * 65]:
                with self.subTest(slug=slug):
                    with self.assertRaisesRegex(ValueError, "invalid application slug"):
                        resolve_app_save_path(temp_dir, slug)

    def test_existing_symlink_cannot_redirect_record_outside_data_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "app_data"
            data_dir.mkdir()
            outside = root / "outside.json"
            outside.write_text("preserve", encoding="utf-8")
            link = data_dir / "safe.json"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "escapes data directory"):
                resolve_app_save_path(data_dir, "safe")
            self.assertEqual(outside.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
