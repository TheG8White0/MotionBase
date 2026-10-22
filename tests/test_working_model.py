"""Synthetic working-model fixtures; no exercises are added to the catalog."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("working_validator", ROOT / "scripts" / "validate_model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)

def variant(exercise_id="PD-EX-900001", grip=None):
    return {
        "exercise_id": exercise_id, "name": "Synthetic schema fixture",
        "family_id": "incline_dumbbell_chest_press", "status": "draft",
        "arm_execution": "bilateral_simultaneous", "bench_angle_degrees": 45,
        "grip": grip or {"behavior": "fixed", "orientation": "neutral"},
        "audit": {"created_on": "2026-10-22", "updated_on": "2026-10-22",
                  "reviewed_by": None, "reviewed_on": None, "revision": 1}
    }

class WorkingModelTests(unittest.TestCase):
    def setUp(self):
        self.data, self.schema = model.load_model()
        self.data = copy.deepcopy(self.data)
        self.data["variants"]["variants"] = [variant()]

    def errors(self):
        return model.validate_model(self.data, self.schema)

    def family(self):
        return next(f for f in self.data["families"]["families"] if f["family_id"] == self.record()["family_id"])

    def record(self):
        return self.data["variants"]["variants"][0]

    def test_empty_working_catalog_and_fixed_profile(self):
        self.assertEqual([], self.errors())
        self.data["variants"]["variants"] = []
        self.assertEqual([], self.errors())

    def test_approved_rotating_example_shape(self):
        self.record()["grip"] = {"behavior": "rotating", "concentric_start": "neutral",
                                "concentric_end": "pronated", "eccentric_behavior": "reverse"}
        self.assertEqual([], self.errors())

    def test_each_listed_family_profile_is_valid(self):
        for profile in self.family()["attribute_rules"]["grip"]["allowed_values"]:
            with self.subTest(profile=profile):
                self.record()["grip"] = profile
                self.assertEqual([], self.errors())

    def test_fixed_grip_rejects_motion_fields(self):
        self.record()["grip"]["concentric_start"] = "neutral"
        self.assertTrue(self.errors())

    def test_rotating_grip_rejects_same_endpoints(self):
        self.record()["grip"] = {"behavior": "rotating", "concentric_start": "neutral",
                                "concentric_end": "neutral", "eccentric_behavior": "reverse"}
        self.assertTrue(self.errors())

    def test_rotating_requires_phase_and_return(self):
        self.record()["grip"] = {"behavior": "rotating", "concentric_start": "neutral",
                                "concentric_end": "pronated"}
        self.assertTrue(self.errors())

    def test_prone_is_not_forearm_orientation(self):
        self.record()["grip"]["orientation"] = "prone"
        self.assertTrue(self.errors())

    def test_globally_valid_but_unlisted_profile_is_rejected(self):
        self.record()["grip"] = {"behavior": "rotating", "concentric_start": "neutral",
                                "concentric_end": "supinated", "eccentric_behavior": "reverse"}
        self.assertTrue(any("not allowed by family" in error for error in self.errors()))

    def test_required_applicable_attribute_cannot_be_omitted(self):
        del self.record()["grip"]
        self.assertTrue(any("family requires grip" in error for error in self.errors()))

    def test_not_applicable_and_unknown_prohibit_values(self):
        for state in ("not_applicable", "unknown"):
            with self.subTest(state=state):
                self.family()["attribute_rules"]["grip"] = {
                    "applicability": state, "required": False, "allowed_values": None,
                    "value_constraints": None, "reason": "Synthetic scope rule."}
                self.assertTrue(any("omit grip" in error for error in self.errors()))
                saved = self.record().pop("grip")
                self.assertEqual([], self.errors())
                self.record()["grip"] = saved

    def test_not_applicable_cannot_be_required(self):
        self.family()["attribute_rules"]["grip"]["applicability"] = "not_applicable"
        self.assertTrue(self.errors())

    def test_null_is_not_a_value_or_applicability_override(self):
        self.record()["grip"] = None
        self.assertTrue(self.errors())
        self.record()["grip"] = {"applicable": False}
        self.assertTrue(self.errors())

    def test_family_limits_arm_execution_and_angle(self):
        self.record()["arm_execution"] = "unilateral"
        self.assertTrue(self.errors())
        self.record()["arm_execution"] = "bilateral_simultaneous"
        for angle in (0, -15, 90, "incline", True):
            with self.subTest(angle=angle):
                self.record()["bench_angle_degrees"] = angle
                self.assertTrue(self.errors())

    def test_unknown_attributes_and_missing_family(self):
        self.record()["sets"] = 3
        self.assertTrue(self.errors())
        del self.record()["sets"]
        self.record()["family_id"] = "missing"
        self.assertTrue(any("unknown family" in error for error in self.errors()))

    def test_framework_fields_are_outside_core(self):
        for field in ("opt_phase", "corrective_stage", "rpe"):
            with self.subTest(field=field):
                self.record()[field] = 1
                self.assertTrue(self.errors())
                del self.record()[field]

    def test_all_families_declare_all_attribute_rules(self):
        del self.family()["attribute_rules"]["grip"]
        self.assertTrue(any("explicitly declare" in error for error in self.errors()))

    def test_category_and_family_cycles(self):
        self.data["attribute_definitions"]["categories"][0]["parent_category_id"] = "arm_coordination"
        self.assertTrue(any("cycle" in error for error in self.errors()))
        self.data["attribute_definitions"]["categories"][0]["parent_category_id"] = None
        self.data["families"]["families"][0]["parent_family_id"] = self.family()["family_id"]
        self.assertTrue(any("cycle" in error for error in self.errors()))

    def test_missing_parent_and_duplicate_ids(self):
        self.family()["parent_family_id"] = "missing"
        self.assertTrue(any("missing parent" in error for error in self.errors()))
        self.family()["parent_family_id"] = "chest_press"
        duplicate = copy.deepcopy(self.family())
        duplicate["name"] = "Different name"
        self.data["families"]["families"].append(duplicate)
        self.assertTrue(any("duplicate ID" in error for error in self.errors()))

    def test_dictionary_examples_and_schema_cannot_drift(self):
        attr = self.data["attribute_definitions"]["attributes"][0]
        attr["examples"].append("not_a_value")
        self.assertTrue(self.errors())
        attr["examples"].pop()
        attr["invalid_examples"][0]["value"] = "unilateral"
        self.assertTrue(any("actually valid" in error for error in self.errors()))
        attr["invalid_examples"][0]["value"] = "bilateral"
        attr["value_schema"]["enum"].append("invented")
        self.assertTrue(any("differs from variant schema" in error for error in self.errors()))

    def test_no_remote_refs_or_ignored_keyword_typos(self):
        attr = self.data["attribute_definitions"]["attributes"][0]
        attr["value_schema"] = {"$ref": "https://example.org/untrusted-schema"}
        self.assertTrue(any("unsupported schema keyword" in error for error in self.errors()))
        attr["value_schema"] = {"type": "number", "minimun": 0}
        self.assertTrue(any("unsupported schema keyword" in error for error in self.errors()))

    def test_malformed_inline_schema_fails_cleanly(self):
        self.data["attribute_definitions"]["attributes"][0]["value_schema"] = {"properties": []}
        self.assertTrue(any("invalid JSON Schema" in error for error in self.errors()))

    def test_rule_schema_is_checked_before_use(self):
        self.family()["attribute_rules"]["bench_angle_degrees"]["value_constraints"] = {"$ref": "https://example.org/no"}
        self.assertTrue(any("unsupported schema keyword" in error for error in self.errors()))

    def test_duplicate_variant_ids_and_duplicate_configurations(self):
        another = variant()
        another["name"] = "Another fixture"
        self.data["variants"]["variants"].append(another)
        self.assertTrue(any("duplicate exercise ID" in error for error in self.errors()))
        another["exercise_id"] = "PD-EX-900002"
        self.assertTrue(any("duplicate family/attribute" in error for error in self.errors()))

    def test_approval_and_audit_rules(self):
        self.record()["status"] = "approved"
        self.assertTrue(self.errors())
        self.record()["audit"].update(reviewed_by="Synthetic reviewer", reviewed_on="2026-10-22")
        self.assertTrue(any("approved family" in error for error in self.errors()))
        self.family()["status"] = "approved"
        self.assertEqual([], self.errors())
        self.record()["audit"]["updated_on"] = "2999-01-01"
        self.assertTrue(self.errors())

    def test_privacy_and_legacy_id_collision(self):
        self.record()["name"] = "sample@example.org"
        self.assertTrue(self.errors())
        self.record()["name"] = "Synthetic fixture"
        self.assertTrue(model.validate_model(self.data, self.schema, {"PD-EX-900001"}))

    def test_compare_distinguishes_grip_without_causal_claims(self):
        left = variant()
        right = variant("PD-EX-900002", {"behavior": "fixed", "orientation": "pronated"})
        comparison = model.compare_variants(left, right, ["arm_execution", "bench_angle_degrees", "grip"])
        self.assertEqual(["grip.orientation"], comparison["differing_attributes"])
        self.assertTrue(comparison["same_family"])
        self.assertNotIn("effect", comparison)
        del right["grip"]
        comparison = model.compare_variants(left, right, ["grip"])
        self.assertEqual(["grip"], comparison["uncompared_attributes"])
        self.assertEqual([], comparison["matching_attributes"])

    def test_baseline_retains_ids_and_revision(self):
        old = copy.deepcopy(self.data["variants"])
        self.assertTrue(model.baseline_errors({"variants": []}, old))
        self.record()["name"] = "Changed fixture"
        self.assertTrue(model.baseline_errors(self.data["variants"], old))
        self.record()["audit"]["revision"] = 2
        self.assertEqual([], model.baseline_errors(self.data["variants"], old))
        self.record()["audit"]["created_on"] = "2026-10-21"
        self.assertTrue(model.baseline_errors(self.data["variants"], old))


    def lower_body(self, loaded=False):
        record = self.record()
        for key in ("arm_execution", "bench_angle_degrees", "grip"):
            record.pop(key, None)
        record.update(family_id=("bilateral_side_held_dumbbell_squat" if loaded
                                 else "bilateral_bodyweight_squat"),
                      leg_execution="bilateral_simultaneous",
                      stance_configuration="bilateral_aligned", stance_width_cm=40)
        if loaded:
            record["grip"] = {"behavior": "fixed", "orientation": "neutral"}
        return record

    def test_bodyweight_squat_requires_stance_without_grip(self):
        record = self.lower_body()
        self.assertEqual([], self.errors())
        record["grip"] = {"behavior": "fixed", "orientation": "neutral"}
        self.assertTrue(any("omit grip" in error for error in self.errors()))

    def test_lower_body_can_require_grip_and_stance_together(self):
        record = self.lower_body(loaded=True)
        self.assertEqual([], self.errors())
        del record["grip"]
        self.assertTrue(any("family requires grip" in error for error in self.errors()))

    def test_stance_width_uses_nonnegative_cm_not_labels(self):
        record = self.lower_body()
        for value in (0, 30, 42.5):
            record["stance_width_cm"] = value
            self.assertEqual([], self.errors())
        for value in (-5, "wide", None, True):
            record["stance_width_cm"] = value
            self.assertTrue(self.errors())
        del record["stance_width_cm"]
        self.assertTrue(any("family requires stance_width_cm" in error for error in self.errors()))

    def test_stance_arrangement_does_not_replace_leg_execution(self):
        record = self.lower_body()
        record["leg_execution"] = "split_stance"
        self.assertTrue(self.errors())
        record["leg_execution"] = "bilateral_simultaneous"
        record["stance_configuration"] = "wide"
        self.assertTrue(self.errors())

    def test_single_leg_support_has_no_two_heel_width(self):
        record = self.lower_body()
        # Synthetic family extension: a contribution would need separate review.
        rules = self.family()["attribute_rules"]
        rules["stance_configuration"]["allowed_values"] = ["single_leg"]
        rules["stance_width_cm"].update(applicability="not_applicable", required=False)
        record["stance_configuration"] = "single_leg"
        self.assertTrue(self.errors())
        del record["stance_width_cm"]
        self.assertEqual([], self.errors())

    def test_press_does_not_accept_unclassified_stance_or_leg_fields(self):
        self.record()["stance_configuration"] = "bilateral_aligned"
        self.record()["stance_width_cm"] = 40
        self.assertTrue(any("omit stance_width_cm" in error for error in self.errors()))

    def test_stance_comparison_reports_width_difference(self):
        left = copy.deepcopy(self.lower_body())
        right = copy.deepcopy(left)
        right["stance_width_cm"] = 45
        result = model.compare_variants(left, right, ["leg_execution", "stance_configuration", "stance_width_cm", "grip"])
        self.assertEqual(["stance_width_cm"], result["differing_attributes"])
        self.assertEqual(["grip"], result["uncompared_attributes"])


    def test_equal_numeric_values_are_duplicate_configurations(self):
        for lower_body in (False, True):
            self.setUp()
            if lower_body:
                self.lower_body()
            field = "stance_width_cm" if lower_body else "bench_angle_degrees"
            another = copy.deepcopy(self.record())
            another["exercise_id"] = "PD-EX-900002"
            another[field] = float(self.record()[field])
            self.data["variants"]["variants"].append(another)
            self.assertTrue(any("duplicate family/attribute" in error for error in self.errors()))
            another[field] += 0.00001
            self.assertEqual([], self.errors())

    def test_family_only_single_leg_cannot_advertise_width(self):
        self.lower_body()
        rules = self.family()["attribute_rules"]
        rules["stance_configuration"]["allowed_values"] = ["single_leg"]
        self.data["variants"]["variants"] = []
        self.assertTrue(any("single-leg-only" in error for error in self.errors()))
        rules["stance_width_cm"].update(applicability="not_applicable", required=False)
        self.assertEqual([], self.errors())

    def test_required_width_requires_known_two_foot_support_rule(self):
        self.lower_body()
        self.family()["attribute_rules"]["stance_configuration"]["required"] = False
        self.data["variants"]["variants"] = []
        self.assertTrue(any("required two-foot" in error for error in self.errors()))

    def test_width_cannot_be_recorded_without_two_foot_configuration(self):
        self.lower_body()
        self.family()["attribute_rules"]["stance_width_cm"]["required"] = False
        self.family()["attribute_rules"]["stance_configuration"]["required"] = False
        del self.record()["stance_configuration"]
        self.assertTrue(self.errors())

if __name__ == "__main__":
    unittest.main()
