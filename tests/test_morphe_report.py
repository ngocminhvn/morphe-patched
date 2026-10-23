#!/usr/bin/env python3
"""Regression tests for Morphe CLI report schema and our required patches."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "build.sh").read_text(encoding="utf-8")
MATCH = re.search(
    r'jq -e --arg pkg "\$PACKAGE_NAME" \'(.*?)\' "\$REPORT"',
    SCRIPT,
    flags=re.DOTALL,
)
if MATCH is None:
    raise RuntimeError("Could not locate Morphe report validation in scripts/build.sh")
FILTER = MATCH.group(1)


def report(package="com.google.android.youtube"):
    return {
        "success": True,
        "packageName": package,
        "packageVersion": "21.20.405",
        "appliedPatches": ["Hide ads", "Disable Play Store updates"],
        "failedPatches": [],
        "stepResults": [
            {"step": "PATCHING", "success": True},
            {"step": "REBUILDING", "success": True},
        ],
    }


def accepted(data, package):
    command = ["jq", "-e", "--arg", "pkg", package, FILTER]
    result = subprocess.run(
        command,
        input=json.dumps(data),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


class MorpheReportTests(unittest.TestCase):
    def test_youtube_successful_report(self):
        self.assertTrue(accepted(report(), "com.google.android.youtube"))

    def test_youtube_music_successful_report(self):
        package = "com.google.android.apps.youtube.music"
        self.assertTrue(accepted(report(package), package))

    def test_missing_update_patch_is_rejected(self):
        data = report()
        data["appliedPatches"].remove("Disable Play Store updates")
        self.assertFalse(accepted(data, data["packageName"]))

    def test_protected_patch_is_rejected(self):
        data = report()
        data["appliedPatches"].append("GmsCore support")
        self.assertFalse(accepted(data, data["packageName"]))

    def test_failed_patch_is_rejected(self):
        data = report()
        data["failedPatches"].append("Something failed")
        self.assertFalse(accepted(data, data["packageName"]))

    def test_failed_step_is_rejected(self):
        data = report()
        data["stepResults"][1]["success"] = False
        self.assertFalse(accepted(data, data["packageName"]))

    def test_signing_step_is_rejected(self):
        data = report()
        data["stepResults"].append({"step": "SIGNING", "success": True})
        self.assertFalse(accepted(data, data["packageName"]))

    def test_wrong_package_is_rejected(self):
        self.assertFalse(accepted(report(), "com.google.android.apps.youtube.music"))


if __name__ == "__main__":
    unittest.main()
