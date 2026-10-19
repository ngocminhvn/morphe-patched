#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from plan_updates import plan_updates


def meta(patch="v1.47.0", yt="21.20.405", music="9.20.53"):
    return {"patchesTag": patch, "apps": {
        "youtube": {"versions": [
            {"version": "21.40.161", "experimental": True},
            {"version": yt, "experimental": False},
        ]},
        "youtube-music": {"versions": [
            {"version": "9.40.51", "experimental": True},
            {"version": music, "experimental": False},
        ]},
    }}


def release(yt="21.20.405", music="9.20.53"):
    return {"tag_name": "morphe-1.47.0", "assets": [
        {"name": f"Youtube-{yt}-morphe-1.47.0-121026.apk"},
        {"name": f"YoutubeMusic-{music}-morphe-1.47.0-191026.apk"},
    ]}


class PlanUpdatesTests(unittest.TestCase):
    def test_no_updates(self):
        p = plan_updates(meta(), release())
        self.assertEqual(p["mode"], "none")
        self.assertEqual(p["apps"], [])
        self.assertFalse(p["should_build"])

    def test_new_morphe_release(self):
        p = plan_updates(meta(patch="v1.48.0"), {})
        self.assertEqual(p["mode"], "new_release")
        self.assertEqual(p["apps"], ["youtube", "youtube-music"])

    def test_new_youtube_stable_only(self):
        p = plan_updates(meta(yt="21.21.103"), release())
        self.assertEqual(p["mode"], "update_existing")
        self.assertEqual(p["apps"], ["youtube"])

    def test_new_music_stable_only(self):
        p = plan_updates(meta(music="9.21.53"), release())
        self.assertEqual(p["apps"], ["youtube-music"])

    def test_experimental_ignored(self):
        self.assertEqual(plan_updates(meta(), release())["apps"], [])

    def test_missing_app_asset_rebuilt(self):
        r = release()
        r["assets"].pop()
        self.assertEqual(plan_updates(meta(), r)["apps"], ["youtube-music"])

    def test_date_change_not_update(self):
        r = release()
        r["assets"][0]["name"] = r["assets"][0]["name"].replace("121026", "191026")
        self.assertFalse(plan_updates(meta(), r)["should_build"])

    def test_no_stable_refuses_build(self):
        m = meta()
        m["apps"]["youtube"]["versions"] = [{"version": "22.0", "experimental": True}]
        with self.assertRaisesRegex(ValueError, "No supported Stable"):
            plan_updates(m, release())


if __name__ == "__main__":
    unittest.main()
