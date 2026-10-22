"""Validate PhysioData structure, references, dosing, and public repository scope."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
ENUM_PATHS = {
    "record_statuses": "status",
    "training_components": "classification.training_components.items",
    "body_regions": "classification.body_regions.items",
    "movement_patterns": "classification.movement_patterns.items",
    "planes": "classification.planes.items",
    "contraction_types": "classification.contraction_types.items",
    "limb_modes": "classification.limb_mode",
    "joint_scopes": "classification.joint_scope",
    "kinetic_chains": "classification.kinetic_chain",
    "positions": "classification.position",
    "support_levels": "classification.support_level",
    "surfaces": "classification.surface",
    "impact_levels": "classification.impact_level",
    "lateral_speeds": "classification.lateral_speed",
    "corrective_focus": "corrective_targets.items.focus",
    "load_metrics": "load_tracking.metric",
    "load_units": "load_tracking.unit_options.items",
    "load_bases": "load_tracking.load_basis",
    "session_roles": "programming_contexts.items.session_role",
    "dose_types": "programming_contexts.items.dosage.dose_type",
    "intensity_measures": "programming_contexts.items.dosage.intensity_measure",
    "source_types": "sources.items.type",
}
PRIVATE_KEYS = {"client_name", "client_id", "patient_name", "patient_id",
                "date_of_birth", "dob", "medical_record_number", "phone",
                "email", "home_address", "client_history", "session_history"}
ROOT_FILES = {"README.md", "CONTRIBUTING.md", "VALIDATION.md", "AGENT_REVIEW.md", "TAXONOMY_REASONING.md",
              "LICENSING.md", "LICENSE", "LICENSE-DATA", "LICENSE-CODE",
              "LICENSE.md", "LICENSE.txt", "exercise.schema.json",
              "exercises.json", "taxonomy.json", "requirements-validation.txt",
              ".gitignore", ".gitattributes"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
DOSES = ("repetitions", "hold_seconds", "work_seconds", "distance_meters")
EFFORTS = ("rpe", "rir", "percent_1rm")
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(?:\+1[ -]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")

def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("non-finite JSON value: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=pairs, parse_constant=invalid_constant)

def walk(value, path=""):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + "/" + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + "/" + str(index))

def schema_node(schema, path):
    node = schema["properties"]["exercises"]["items"]
    for part in path.split("."):
        node = node["items"] if part == "items" else node["properties"][part]
    return node

def check_taxonomy(taxonomy, schema):
    errors = []
    if taxonomy.get("project_name") != "PhysioData":
        errors.append("taxonomy: project_name must be PhysioData")
    if taxonomy.get("schema_version") != schema["properties"]["schema_version"]["const"]:
        errors.append("taxonomy: schema_version differs from schema")
    mappings = dict(ENUM_PATHS)
    mappings["corrective_stages"] = "programming_contexts.items.corrective_stage"
    for key, path in mappings.items():
        values = taxonomy.get(key)
        if (not isinstance(values, list) or not values or
                any(not isinstance(x, str) or not x.strip() for x in values)):
            errors.append("taxonomy: invalid category " + key)
            continue
        if len(values) != len(set(values)):
            errors.append("taxonomy: duplicate value in " + key)
        expected = [x for x in schema_node(schema, path)["enum"] if x is not None]
        if set(values) != set(expected):
            errors.append("taxonomy/schema mismatch: " + key)
    for path in ("corrective_targets.items.body_region",):
        if set(schema_node(schema, path)["enum"]) != set(taxonomy.get("body_regions", [])):
            errors.append("taxonomy/schema mismatch: corrective target regions")
    phases = taxonomy.get("opt_phases", {})
    if not isinstance(phases, dict) or set(phases) != {"1", "2", "3", "4", "5"}:
        errors.append("taxonomy: OPT must contain phases 1 through 5")
    if taxonomy.get("opt_levels") != {"stabilization": [1], "strength": [2, 3, 4], "power": [5]}:
        errors.append("taxonomy: OPT level/phase mapping is inconsistent")
    if set(schema_node(schema, "programming_contexts.items.opt_phase")["enum"]) != {1, 2, 3, 4, 5, None}:
        errors.append("schema: invalid OPT phases")
    return errors

def check_privacy(data):
    errors = []
    for path, value in walk(data):
        if isinstance(value, dict):
            for key in value:
                if key.lower() in PRIVATE_KEYS:
                    errors.append(path + ": client/contact field is prohibited: " + key)
        if isinstance(value, str):
            if not value.strip():
                errors.append(path + ": blank strings must be omitted or null where permitted")
            if EMAIL.search(value) or PHONE.search(value):
                errors.append(path + ": possible personal contact information; review/remove")
            if re.search(r"(?i)(?:\b[A-Z]:[\\/]|file://|/Users/|/home/)", value):
                errors.append(path + ": local/private filesystem path is prohibited")
    return errors

def duplicates(values):
    return sorted(key for key, count in Counter(values).items() if count > 1)

def check_semantics(records):
    errors = []
    ids = {r["exercise_id"] for r in records}
    for repeated in duplicates(r["exercise_id"] for r in records):
        errors.append("duplicate exercise ID: " + repeated)
    today = date.today().isoformat()
    for record in records:
        label = record["exercise_id"]
        def fail(message):
            errors.append(label + ": " + message)
        for part in ("aliases",):
            names = [x.casefold().strip() for x in record.get(part, [])]
            if len(names) != len(set(names)):
                fail("duplicate aliases after case/space normalization")
        sources = record.get("sources", [])
        source_ids = {s["source_id"] for s in sources}
        for repeated in duplicates(s["source_id"] for s in sources):
            fail("duplicate source ID " + repeated)
        for source in sources:
            if source["url"] is not None:
                url = urlparse(source["url"])
                if url.scheme not in ("https", "http") or not url.netloc or url.username or url.password:
                    fail("source URL must be a public HTTP(S) URL without credentials")
            if source["type"] != "coach_practice" and (not source["url"] or not source["checked_on"]):
                fail("external reference requires URL and checked_on")
            if source["checked_on"] and source["checked_on"] > today:
                fail("source checked_on cannot be in the future")
        def links(values, purpose):
            for value in values:
                if value not in source_ids:
                    fail(purpose + " links to unknown source " + value)
        for target in record.get("corrective_targets", []):
            if not any(c["corrective_stage"] is not None for c in record.get("programming_contexts", [])):
                fail("corrective targets need a corrective programming context")
        selection = record.get("selection", {})
        for key in ("regression_ids", "progression_ids", "substitution_ids"):
            for linked in selection.get(key, []):
                if linked == label or linked not in ids:
                    fail(key + " must link to another existing exercise: " + linked)
                elif record["status"] == "approved":
                    target_record = next(r for r in records if r["exercise_id"] == linked)
                    if target_record["status"] != "approved":
                        fail(key + " must link to an approved exercise")
        for precaution in selection.get("precautions", []):
            links(precaution["source_ids"], "precaution")
        classification = record.get("classification", {})
        if "not_applicable" in classification.get("contraction_types", []) and len(classification["contraction_types"]) != 1:
            fail("not_applicable contraction cannot be combined with active contractions")
        load = record.get("load_tracking")
        if load:
            units = {"external_mass": {"lb", "kg"}, "band_setting": {"band_label"},
                     "machine_setting": {"machine_setting", "lb", "kg"},
                     "bodyweight": {"bodyweight"}, "assistance_setting": {"assistance_setting", "lb", "kg"},
                     "none": {"none"}}
            bases = {"external_mass": {"total", "per_hand", "per_side"},
                     "band_setting": {"not_applicable", "per_side", "total"},
                     "machine_setting": {"stack_display"},
                     "bodyweight": {"not_applicable"}, "assistance_setting": {"assistance"},
                     "none": {"not_applicable"}}
            if not set(load["unit_options"]) <= units[load["metric"]] or load["load_basis"] not in bases[load["metric"]]:
                fail("load metric, units and load basis are inconsistent")
        contexts = record.get("programming_contexts", [])
        for repeated in duplicates(c["context_id"] for c in contexts):
            fail("duplicate context ID " + repeated)
        for context in contexts:
            prefix = context["context_id"] + ": "
            links(context["source_ids"], prefix + "context")
            dosage = context["dosage"]
            for path, value in walk(dosage):
                if isinstance(value, dict) and set(value) == {"min", "max"}:
                    low, high = value["min"], value["max"]
                    if (low is None) != (high is None):
                        fail(prefix + path + " needs both endpoints or two nulls")
                    if low is not None and high is not None and low > high:
                        fail(prefix + path + " minimum exceeds maximum")
            selected = dosage["dose_type"]
            for key in ("sets", selected):
                if any(dosage[key][bound] is None or dosage[key][bound] <= 0 for bound in ("min", "max")):
                    fail(prefix + key + " requires positive minimum and maximum")
            for key in DOSES:
                if key != selected and any(v is not None for v in dosage[key].values()):
                    fail(prefix + "inactive dose must be null: " + key)
            measure = dosage["intensity_measure"]
            allowed = {"rpe_rir": {"rpe", "rir"}, "rpe_0_10": {"rpe"},
                       "percent_1rm": {"percent_1rm"}}.get(measure, set())
            for key in EFFORTS:
                filled = any(v is not None for v in dosage[key].values())
                if key not in allowed and filled:
                    fail(prefix + key + " does not match intensity measure")
            if allowed and not any(dosage[key]["min"] is not None for key in allowed):
                fail(prefix + "selected intensity measure requires a target")
        audit = record.get("audit")
        if audit:
            if audit["created_on"] > audit["updated_on"] or audit["updated_on"] > today:
                fail("audit dates must be ordered and not in the future")
            if audit["reviewed_on"] and (audit["reviewed_on"] < audit["created_on"] or audit["reviewed_on"] > today):
                fail("reviewed_on must follow creation and not be in the future")
            if record["status"] == "approved" and audit["reviewed_on"] < audit["updated_on"]:
                fail("approval must cover latest update")
    return errors

def validate_data(database, taxonomy, schema):
    Draft202012Validator.check_schema(schema)
    errors = check_taxonomy(taxonomy, schema)
    errors.extend(check_privacy(database))
    errors.extend(check_privacy(taxonomy))
    shape_errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(database),
                          key=lambda error: str(list(error.absolute_path)))
    for error in shape_errors:
        path = "/".join(str(x) for x in error.absolute_path)
        errors.append("schema /" + path + ": " + error.message)
    if not shape_errors:
        errors.extend(check_semantics(database["exercises"]))
    return errors

def validate_baseline(database, baseline):
    errors = []
    current = {r["exercise_id"]: r for r in database["exercises"]}
    for old in baseline["exercises"]:
        exercise_id = old["exercise_id"]
        new = current.get(exercise_id)
        if new is None:
            errors.append(exercise_id + ": accepted IDs must be retained; retire instead of deleting")
            continue
        if old != new and "audit" in old:
            if "audit" not in new or new["audit"]["revision"] <= old["audit"]["revision"]:
                errors.append(exercise_id + ": changed records require a higher revision")
            if "audit" not in new or new["audit"]["created_on"] != old["audit"]["created_on"]:
                errors.append(exercise_id + ": created_on is immutable")
    return errors

def allowed_path(relative):
    parts = relative.parts
    if not parts:
        return False
    if len(parts) == 1:
        return parts[0] in ROOT_FILES
    if parts[0] == "working-model":
        return len(parts) == 2 and parts[1] in {
            "schema.json", "attribute-definitions.json", "families.json", "variants.json"}
    if parts[0] in {"scripts", "tests"}:
        return relative.suffix == ".py"
    if parts[0] == "docs":
        return relative.suffix == ".md"
    if parts[0] == ".github":
        return relative.suffix in {".yml", ".yaml", ".md"} or relative.name == "CODEOWNERS"
    return False

def check_scope(root):
    errors = []
    pending = [root]
    while pending:
        directory = pending.pop()
        for child in directory.iterdir():
            relative = child.relative_to(root)
            if child.is_symlink():
                errors.append("public scope: symlinks prohibited: " + relative.as_posix())
            elif child.is_dir():
                if child.name not in SKIP_DIRS:
                    pending.append(child)
            elif child.suffix != ".pyc" and not allowed_path(relative):
                errors.append("public scope: unexpected file: " + relative.as_posix())
    return errors

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--base-ref", help="Git commit/ref used to preserve accepted IDs and revisions")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        database = read_json(root / "exercises.json")
        taxonomy = read_json(root / "taxonomy.json")
        schema = read_json(root / "exercise.schema.json")
        errors = validate_data(database, taxonomy, schema) + check_scope(root)
        if args.base_ref and not errors:
            result = subprocess.run(["git", "-C", str(root), "show", args.base_ref + ":exercises.json"],
                                    capture_output=True, text=True, check=True)
            baseline = json.loads(result.stdout.lstrip("\ufeff"))
            errors.extend(validate_baseline(database, baseline))
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print("FAIL: validation could not complete: " + str(error), file=sys.stderr)
        return 1
    if errors:
        print("\n".join("FAIL: " + error for error in errors), file=sys.stderr)
        return 1
    print("PASS: PhysioData validation (" + str(len(database["exercises"])) + " exercise records)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
