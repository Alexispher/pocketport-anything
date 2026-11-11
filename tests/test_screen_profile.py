"""Declarative 3DS screen layout/port assessment regression tests."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path

from pocketport.screens import (
    ScreenProfileError, load_profile, validate_profile, make_header,
    assess_profile, write_header,
)

ROOT=Path(__file__).resolve().parents[1]
PROFILE=ROOT/"examples"/"source-port"/"display-profile.json"


class ScreenProfileTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(PROFILE.read_text(encoding="utf-8"))

    def test_real_screen_dimensions(self):
        result=assess_profile(self.data)
        self.assertEqual(result["hardware"]["top_logical_pixels"], [400,240])
        self.assertEqual(result["hardware"]["bottom_logical_pixels"], [320,240])
        self.assertIsNone(result["hardware"]["application_ram_grant"])
        self.assertFalse(result["verified"]["native_build"])

    def test_allows_configuration_without_false_hardware_claim(self):
        self.data["target"]="old3ds"
        self.data["displays"]["bottom"]="map"
        p=assess_profile(self.data)
        self.assertEqual(p["target"],"old3ds")
        self.assertEqual(p["layout"]["bottom"],"map")
        self.assertFalse(p["verified"]["emulator_visual"])

    def test_rejects_unknown_fields(self):
        self.data["mystery"]="unverified"
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)

    def test_rejects_schema_change(self):
        self.data["schema_version"]=2
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)

    def test_rejects_touch_without_fallback(self):
        self.data["touch"]["physical_fallback"]=False
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)

    def test_rejects_bad_touch_modes(self):
        self.data["touch"]["mode"]="magic"
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)
        self.data["touch"]["mode"]="disabled"
        self.data["source"]["touch_required"]=True
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)

    def test_rejects_incompatible_pages(self):
        self.data["pages"]=["hud","hud","pause","help"]
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)
        self.data["pages"]=["map","pause","help"]
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)

    def test_rejects_unsupported_controls(self):
        self.data["controls"]["bindings"]["pause"]=["unknown_button"]
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)

    def test_rejects_unmeasured_memory_grant(self):
        self.data["resources"]["application_ram_budget_bytes"]=80000000
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)
        self.data["resources"]["source"]="measured"
        self.assertEqual(assess_profile(self.data)["hardware"]["application_ram_grant"], 80000000)

    def test_stereo_request_is_not_native_implementation(self):
        self.data["graphics"]["stereo_requested"]=True
        result=assess_profile(self.data)
        self.assertIn("Native stereoscopic renderer not implemented or verified",
                      result["missing_or_unsupported"])
        with self.assertRaises(ScreenProfileError):
            make_header(self.data)

    def test_header_controls_initial_screen_and_pages(self):
        self.data["displays"]["bottom"]="map"
        self.data["pages"]=["hud","map","pause","help"]
        code=make_header(self.data)
        self.assertIn("#define PP_PROFILE_INITIAL_PAGE PP_PAGE_MAP",code)
        self.assertIn("PP_UI_ALLOW_MAP",code)
        self.assertNotIn("PP_UI_ALLOW_INVENTORY",code)

    def test_roundtrip_and_refuse_invalid_profile(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"profile.json"
            source.write_text(json.dumps(self.data),encoding="utf-8")
            loaded=load_profile(source)
            self.assertEqual(loaded["schema_version"],1)
            output=write_header(Path(td)/"out"/"profile.h",loaded)
            self.assertGreater(output["bytes"],100)
            self.assertTrue(Path(output["output"]).is_file())
            source.write_text('{"schema_version": 999}',encoding="utf-8")
            with self.assertRaises(ScreenProfileError):
                load_profile(source)

    def test_native_key_bindings_are_generated(self):
        self.data["controls"]["bindings"]["pause"]=["a"]
        self.data["controls"]["bindings"]["confirm"]=["x"]
        code=make_header(self.data)
        self.assertIn("#define PP_PROFILE_BIND_PAUSE (PP_UI_KEY_A)",code)
        self.assertIn("#define PP_PROFILE_BIND_CONFIRM (PP_UI_KEY_X)",code)

    def test_unmapped_native_control_is_rejected(self):
        self.data["controls"]["bindings"]["pause"]=["circle_left"]
        with self.assertRaises(ScreenProfileError):
            validate_profile(self.data)

    def test_explicit_evidence_only(self):
        with self.assertRaises(ScreenProfileError):
            assess_profile(self.data,{"emulator_tested":"yes"})
        self.assertTrue(assess_profile(self.data,{"native_build_verified":True})["verified"]["native_build"])


if __name__ == "__main__":
    unittest.main()
