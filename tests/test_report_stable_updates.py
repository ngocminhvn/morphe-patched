#!/usr/bin/env python3
"""Regression tests for GitHub Actions' no-update decision summary."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_stable_updates import evaluate  # noqa: E402

META = {
    "patchesTag": "v1.46.0",
    "apps": {
        "youtube": {"versions": [
            {"version": "21.40.161", "experimental": True},
            {"version": "21.16.256", "experimental": False},
        ]},
        "youtube-music": {"versions": [
            {"version": "9.40.51", "experimental": True},
            {"version": "9.20.53", "experimental": False},
        ]},
        "reddit": {"versions": [
            {"version": "2026.40.0", "experimental": True},
            {"version": "2026.24.0", "experimental": False},
        ]},
    },
}
ASSETS = [
    "Youtube-21.16.256-morphe-1.46.0-091026.apk",
    "YoutubeMusic-9.20.53-morphe-1.46.0-091026.apk",
    "Reddit-2026.24.0-morphe-1.46.0-091026.apk",
]


class StableReportTest(unittest.TestCase):
    def test_all_stable_assets_present(self):
        status, report = evaluate(META, ASSETS, "success")
        self.assertEqual(status, "no-update")
        self.assertIn("Không có cập nhật Stable mới", report)
        self.assertIn("21.16.256", report)
        self.assertNotIn("21.40.161", report)
        self.assertIn("bỏ qua build", report)

    def test_date_change_is_not_an_update(self):
        new_date = [name.replace("091026", "101026") for name in ASSETS]
        status, report = evaluate(META, new_date, "success")
        self.assertEqual(status, "no-update")
        self.assertIn("morphe-1.46.0", report)

    def test_old_needcorepatch_assets_are_migrated_once(self):
        legacy = [name.replace("091026", "NeedCorePatch") for name in ASSETS]
        status, report = evaluate(META, legacy, "success")
        self.assertEqual(status, "pending-publish")
        self.assertIn("3 APK Stable", report)

    def test_one_missing_asset(self):
        status, report = evaluate(META, ASSETS[:-1], "success")
        self.assertEqual(status, "pending-publish")
        self.assertIn("1 APK Stable", report)
        self.assertIn("Thiếu", report)

    def test_missing_asset_and_failed_build(self):
        status, report = evaluate(META, [], "failure")
        self.assertEqual(status, "check-failed")
        self.assertIn("Cần xem log", report)

    def test_empty_stable_set_is_error(self):
        data = {
            "patchesTag": "v1.46.0",
            "apps": {**META["apps"], "youtube": {"versions": [
                {"version": "21.40.161", "experimental": True},
            ]}},
        }
        with self.assertRaisesRegex(ValueError, "No stable Morphe target"):
            evaluate(data, [], "success")

    def test_exact_asset_name_includes_patch_version(self):
        stale = [name.replace("1.46.0", "1.45.0") for name in ASSETS]
        status, report = evaluate(META, stale, "success")
        self.assertEqual(status, "pending-publish")
        self.assertIn("3 APK Stable", report)


if __name__ == "__main__":
    unittest.main()
