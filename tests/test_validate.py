"""Regression tests use synthetic records only; none are published as exercises."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("physiodata_validator", ROOT / "scripts" / "validate.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def span(low=None, high=None):
    return {"min": low, "max": high}

def fixture():
    dosage = {key: span() for key in (*v.DOSES, *v.EFFORTS)}
    dosage.update({
        "dose_type": "repetitions", "sets": span(2, 3), "repetitions": span(8, 12),
        "count_basis": "total", "intensity_measure": "rpe_rir", "rpe": span(7, 8),
        "tempo": {"eccentric_seconds": 2, "hold_after_eccentric_seconds": 0,
                  "concentric_seconds": 2, "hold_after_concentric_seconds": 0,
                  "intent": "Synthetic test value"},
        "rest_seconds": span(30, 60), "estimated_setup_seconds": None,
        "estimated_block_seconds": None, "notes": None})
    return {
        "exercise_id": "PD-EX-000001", "name": "Synthetic validation fixture",
        "aliases": [], "family": None, "status": "approved",
        "classification": {
            "training_components": ["resistance"], "body_regions": ["whole_body"],
            "joints": ["synthetic_joint"], "joint_actions": ["synthetic_action"],
            "primary_muscles": ["synthetic_muscle"], "secondary_muscles": [],
            "movement_patterns": ["squat"], "planes": ["sagittal"],
            "contraction_types": ["concentric", "eccentric"], "limb_mode": "bilateral",
            "joint_scope": "multi_joint", "kinetic_chain": "closed",
            "position": "standing", "support_level": "unsupported", "surface": "stable",
            "impact_level": "none", "lateral_speed": "none", "ballistic": False},
        "corrective_targets": [], "equipment": {"required": [], "optional": [], "setup_notes": None},
        "instructions": {"setup": "Synthetic setup.", "execution": "Synthetic execution.",
                         "cues": ["Synthetic cue."], "common_errors": []},
        "load_tracking": {"metric": "bodyweight", "unit_options": ["bodyweight"],
                          "load_basis": "not_applicable", "notes": None},
        "programming_contexts": [{"context_id": "CTX-001", "opt_phase": 1,
                                  "corrective_stage": None, "session_role": "primary_strength",
                                  "selection_criteria": "Test only.", "dosage": dosage,
                                  "source_ids": ["SRC-001"]}],
        "selection": {"demands": [], "precautions": [], "regression_ids": [],
                      "progression_ids": [], "substitution_ids": []},
        "sources": [{"source_id": "SRC-001", "type": "coach_practice",
                     "title": "Synthetic fixture", "url": None, "locator": None,
                     "checked_on": None, "supports": "Test only."}],
        "audit": {"created_on": "2026-01-01", "updated_on": "2026-01-01",
                  "reviewed_by": "Synthetic reviewer", "reviewed_on": "2026-01-01",
                  "revision": 1, "notes": None}}

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.schema = v.read_json(ROOT / "exercise.schema.json")
        self.taxonomy = v.read_json(ROOT / "taxonomy.json")
        self.record = fixture()

    def errors(self, records=None):
        return v.validate_data({"schema_version": "1.0.0",
                                "exercises": [self.record] if records is None else records},
                               self.taxonomy, self.schema)

    def test_empty_database_and_complete_fixture_pass(self):
        self.assertEqual([], self.errors([]))
        self.assertEqual([], self.errors())

    def test_draft_can_be_minimal_but_cannot_be_approved(self):
        draft = {"exercise_id": "PD-EX-000002", "name": "Synthetic draft", "status": "draft"}
        self.assertEqual([], self.errors([draft]))
        draft["status"] = "approved"
        self.assertTrue(self.errors([draft]))

    def test_schema_rejects_invalid_field_values(self):
        for key, value in (("exercise_id", "DF-EX-000001"), ("status", "published"),
                           ("client_name", "Synthetic prohibited value")):
            with self.subTest(key=key):
                record = fixture()
                record[key] = value
                self.assertTrue(self.errors([record]))

    def test_duplicate_exercise_ids(self):
        other = copy.deepcopy(self.record)
        other["name"] = "Different synthetic name"
        self.assertTrue(any("duplicate exercise ID" in e for e in self.errors([self.record, other])))

    def test_taxonomy_drift(self):
        self.taxonomy["planes"].append("invented")
        self.assertTrue(any("taxonomy/schema mismatch" in e for e in self.errors()))

    def test_duplicate_taxonomy_value(self):
        self.taxonomy["planes"].append("sagittal")
        self.assertTrue(self.errors())

    def test_broken_and_self_links(self):
        for target in ("PD-EX-000099", "PD-EX-000001"):
            with self.subTest(target=target):
                self.record["selection"]["regression_ids"] = [target]
                self.assertTrue(self.errors())

    def test_links_to_drafts_are_not_approved(self):
        draft = {"exercise_id": "PD-EX-000002", "name": "Synthetic draft", "status": "draft"}
        self.record["selection"]["regression_ids"] = [draft["exercise_id"]]
        self.assertTrue(any("approved exercise" in e for e in self.errors([self.record, draft])))

    def test_missing_and_duplicate_sources(self):
        self.record["programming_contexts"][0]["source_ids"] = ["SRC-404"]
        self.assertTrue(self.errors())
        self.record = fixture()
        duplicate = copy.deepcopy(self.record["sources"][0])
        duplicate["title"] = "Different synthetic title"
        self.record["sources"].append(duplicate)
        self.assertTrue(self.errors())

    def test_duplicate_context_ids(self):
        context = copy.deepcopy(self.record["programming_contexts"][0])
        context["selection_criteria"] = "Different synthetic context"
        self.record["programming_contexts"].append(context)
        self.assertTrue(self.errors())

    def test_invalid_dose_ranges(self):
        for key, value in (("sets", span(0, 3)), ("sets", span(3, 2)),
                           ("repetitions", span(None, 10)), ("repetitions", span(12, 8))):
            with self.subTest(key=key, value=value):
                self.record = fixture()
                self.record["programming_contexts"][0]["dosage"][key] = value
                self.assertTrue(self.errors())

    def test_inactive_dose_and_mismatched_effort(self):
        dosage = self.record["programming_contexts"][0]["dosage"]
        dosage["hold_seconds"] = span(10, 20)
        self.assertTrue(self.errors())
        dosage["hold_seconds"] = span()
        dosage["percent_1rm"] = span(60, 70)
        self.assertTrue(self.errors())

    def test_time_based_corrective_context_without_rpe(self):
        context = self.record["programming_contexts"][0]
        context.update(opt_phase=None, corrective_stage="activate", session_role="corrective")
        dose = context["dosage"]
        dose.update(dose_type="hold_seconds", repetitions=span(), hold_seconds=span(10, 20),
                    intensity_measure="technique_quality", rpe=span())
        self.assertEqual([], self.errors())

    def test_context_requires_phase_or_corrective_stage(self):
        self.record["programming_contexts"][0]["opt_phase"] = None
        self.assertTrue(self.errors())

    def test_load_units_and_basis(self):
        self.record["load_tracking"]["unit_options"] = ["lb"]
        self.assertTrue(self.errors())

    def test_dates_and_latest_review(self):
        for field, value in (("created_on", "2026-02-30"), ("updated_on", "2999-01-01"),
                             ("reviewed_on", "2025-12-31")):
            with self.subTest(field=field):
                self.record = fixture()
                self.record["audit"][field] = value
                self.assertTrue(self.errors())
        self.record = fixture()
        self.record["audit"]["updated_on"] = "2026-01-02"
        self.assertTrue(self.errors())

    def test_privacy_inside_free_text(self):
        for text in ("sample@example.org", "212-555-0100", "C:/Users/Example/private",
                     "file:///private/data", "   "):
            with self.subTest(text=text):
                self.record["instructions"]["setup"] = text
                self.assertTrue(self.errors())

    def test_external_reference_needs_traceable_url_and_date(self):
        self.record["sources"][0]["type"] = "nasm"
        self.assertTrue(self.errors())
        self.record["sources"][0].update(url="https://example.org/test", checked_on="2026-01-01")
        self.assertEqual([], self.errors())

    def test_invalid_public_reference_url(self):
        self.record["sources"][0]["url"] = "https://user:password@example.org/test"
        self.assertTrue(self.errors())

    def test_baseline_prevents_deletion_and_requires_revision(self):
        baseline = {"exercises": [copy.deepcopy(self.record)]}
        self.assertTrue(v.validate_baseline({"exercises": []}, baseline))
        self.record["name"] = "Updated synthetic name"
        self.assertTrue(v.validate_baseline({"exercises": [self.record]}, baseline))
        self.record["audit"]["revision"] = 2
        self.assertEqual([], v.validate_baseline({"exercises": [self.record]}, baseline))

    def test_repository_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "README.md").write_text("Synthetic test")
            self.assertEqual([], v.check_scope(root))
            (root / "client-notes.csv").write_text("Synthetic test")
            self.assertTrue(v.check_scope(root))

    def test_duplicate_json_keys_and_nonfinite_numbers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            for text in ('{"x": 1, "x": 2}', '{"x": NaN}', '{"x": Infinity}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    v.read_json(path)

if __name__ == "__main__":
    unittest.main()
