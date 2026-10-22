"""Validate the framework-neutral PhysioData working model (v2)."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]
KEYWORDS = {
    "type", "enum", "const", "minimum", "maximum", "exclusiveMinimum",
    "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "pattern",
    "format", "required", "properties", "additionalProperties", "items",
    "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties",
    "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
    "dependentRequired", "dependentSchemas", "propertyNames", "description", "title"
}

def legacy_module():
    spec = importlib.util.spec_from_file_location("physiodata_legacy", ROOT / "scripts" / "validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_model(root=ROOT):
    legacy = legacy_module()
    folder = root / "working-model"
    return {
        "attribute_definitions": legacy.read_json(folder / "attribute-definitions.json"),
        "families": legacy.read_json(folder / "families.json"),
        "variants": legacy.read_json(folder / "variants.json")
    }, legacy.read_json(folder / "schema.json")

def schema_errors(schema, value, label):
    return [label + ": " + error.message
            for error in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value)]

def restricted_schema_errors(schema, label):
    """Only local inline schema vocabulary; reject remote refs and ignored keyword typos."""
    errors = []
    if isinstance(schema, bool):
        return errors
    if not isinstance(schema, dict):
        return [label + ": schema must be an object or boolean"]
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        return [label + ": invalid JSON Schema: " + error.message]
    for key in schema:
        if key not in KEYWORDS:
            errors.append(label + ": unsupported schema keyword " + key)
    for key in ("properties", "dependentSchemas"):
        for child_name, child in schema.get(key, {}).items():
            errors.extend(restricted_schema_errors(child, label + "/" + key + "/" + child_name))
    for key in ("allOf", "anyOf", "oneOf"):
        for index, child in enumerate(schema.get(key, [])):
            errors.extend(restricted_schema_errors(child, label + "/" + key + "/" + str(index)))
    for key in ("not", "if", "then", "else", "items", "additionalProperties", "propertyNames"):
        if key in schema:
            errors.extend(restricted_schema_errors(schema[key], label + "/" + key))
    return errors

def hierarchy_errors(records, id_key, parent_key, label):
    errors = []
    counts = Counter(record[id_key] for record in records)
    for key, count in counts.items():
        if count > 1:
            errors.append(label + ": duplicate ID " + key)
    by_id = {record[id_key]: record for record in records}
    for record in records:
        current = record[id_key]
        seen = set()
        while current is not None:
            if current in seen:
                errors.append(label + ": hierarchy cycle at " + record[id_key])
                break
            if current not in by_id:
                errors.append(label + ": missing parent " + current)
                break
            seen.add(current)
            current = by_id[current][parent_key]
    return errors

def configuration_key(value):
    """JSON numbers with equal values have equal identities, without rounding."""
    def normalize(item):
        if isinstance(item, dict):
            return {key: normalize(child) for key, child in item.items()}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        if isinstance(item, float) and item.is_integer():
            return int(item)
        return item
    return json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)

def validate_model(data, schema, legacy_ids=()):
    errors = []
    Draft202012Validator.check_schema(schema)
    # The shipped bundle is also inline; never resolve arbitrary remote schemas.
    root_schema = dict(schema)
    root_schema.pop("$schema", None)
    root_errors = restricted_schema_errors(root_schema, "model schema")
    if root_errors:
        return root_errors
    shape = schema_errors(schema, data, "model")
    errors.extend(shape)
    if shape:
        return errors
    legacy = legacy_module()
    errors.extend(legacy.check_privacy(data))
    definitions = data["attribute_definitions"]
    categories = definitions["categories"]
    attrs = definitions["attributes"]
    families = data["families"]["families"]
    variants = data["variants"]["variants"]
    errors.extend(hierarchy_errors(categories, "category_id", "parent_category_id", "categories"))
    errors.extend(hierarchy_errors(families, "family_id", "parent_family_id", "families"))
    attr_ids = [attribute["attribute_id"] for attribute in attrs]
    if len(attr_ids) != len(set(attr_ids)):
        errors.append("attributes: duplicate attribute ID")
    by_attr = {attribute["attribute_id"]: attribute for attribute in attrs}
    category_ids = {category["category_id"] for category in categories}
    variant_properties = schema["properties"]["variants"]["properties"]["variants"]["items"]["properties"]
    metadata_fields = {"exercise_id", "name", "family_id", "status", "audit"}
    if set(variant_properties) - metadata_fields != set(by_attr):
        errors.append("attributes: dictionary and variant property names differ")
    invalid_attribute_schemas = set()
    for attribute in attrs:
        key = attribute["attribute_id"]
        if attribute["category_id"] not in category_ids:
            errors.append(key + ": unknown category")
        rule_schema = attribute["value_schema"]
        problem = restricted_schema_errors(rule_schema, key)
        errors.extend(problem)
        if problem:
            invalid_attribute_schemas.add(key)
            continue
        if variant_properties.get(key) != rule_schema:
            errors.append(key + ": dictionary value_schema differs from variant schema")
        for example in attribute["examples"]:
            errors.extend(schema_errors(rule_schema, example, key + " valid example"))
        for example in attribute["invalid_examples"]:
            if not schema_errors(rule_schema, example["value"], key):
                errors.append(key + ": invalid example is actually valid")
    by_family = {family["family_id"]: family for family in families}
    invalid_constraints = set()
    for family in families:
        family_id = family["family_id"]
        rules = family["attribute_rules"]
        if set(rules) != set(by_attr):
            errors.append(family_id + ": explicitly declare applicability for every attribute")
        for key, rule in rules.items():
            if key not in by_attr or key in invalid_attribute_schemas:
                continue
            constraints = rule["value_constraints"]
            if constraints is not None:
                problem = restricted_schema_errors(constraints, family_id + "/" + key)
                errors.extend(problem)
                if problem:
                    invalid_constraints.add((family_id, key))
            for value in rule["allowed_values"] or []:
                errors.extend(schema_errors(by_attr[key]["value_schema"], value, family_id + "/" + key + " allowed value"))
                if constraints is not None and (family_id, key) not in invalid_constraints:
                    errors.extend(schema_errors(constraints, value, family_id + "/" + key + " constrained allowed value"))

        # Cross-attribute support geometry must be coherent even with no variants.
        stance_rule = rules.get("stance_configuration")
        width_rule = rules.get("stance_width_cm")
        if stance_rule and width_rule and "stance_configuration" not in invalid_attribute_schemas:
            choices = []
            if stance_rule["applicability"] == "applicable":
                for choice in by_attr["stance_configuration"]["value_schema"].get("enum", []):
                    if stance_rule["allowed_values"] is not None and choice not in stance_rule["allowed_values"]:
                        continue
                    constraint = stance_rule["value_constraints"]
                    if constraint is not None and (family_id, "stance_configuration") not in invalid_constraints:
                        if schema_errors(constraint, choice, "stance"):
                            continue
                    choices.append(choice)
            if choices == ["single_leg"] and width_rule["applicability"] != "not_applicable":
                errors.append(family_id + ": single-leg-only support requires stance_width_cm not_applicable")
            if width_rule["applicability"] == "applicable" and width_rule["required"]:
                if (not stance_rule["required"] or
                        not set(choices) & {"bilateral_aligned", "bilateral_staggered"}):
                    errors.append(family_id + ": required width needs required two-foot stance configuration")
    seen_ids = set()
    seen_configs = set()
    today = date.today().isoformat()
    for variant in variants:
        exercise_id = variant["exercise_id"]
        if exercise_id in seen_ids:
            errors.append("variants: duplicate exercise ID " + exercise_id)
        if exercise_id in legacy_ids:
            errors.append(exercise_id + ": legacy ID requires an explicit migration plan before reuse")
        seen_ids.add(exercise_id)
        family = by_family.get(variant["family_id"])
        if family is None:
            errors.append(exercise_id + ": unknown family")
            continue
        if family["status"] == "retired":
            errors.append(exercise_id + ": family is retired")
        if variant["status"] == "approved" and family["status"] != "approved":
            errors.append(exercise_id + ": approved variant requires an approved family")
        for key, rule in family["attribute_rules"].items():
            if key not in by_attr or key in invalid_attribute_schemas:
                continue
            present = key in variant
            if rule["applicability"] != "applicable":
                if present:
                    errors.append(exercise_id + ": omit " + key + " when applicability is " + rule["applicability"])
                continue
            if rule["required"] and not present:
                errors.append(exercise_id + ": family requires " + key)
            if present:
                value = variant[key]
                if rule["allowed_values"] is not None and value not in rule["allowed_values"]:
                    errors.append(exercise_id + ": " + key + " profile/value not allowed by family")
                if rule["value_constraints"] is not None and (family["family_id"], key) not in invalid_constraints:
                    errors.extend(schema_errors(rule["value_constraints"], value, exercise_id + "/" + key))
        config = configuration_key({"family_id": variant["family_id"],
                                    **{key: variant[key] for key in by_attr if key in variant}})
        if config in seen_configs:
            errors.append(exercise_id + ": duplicate family/attribute configuration")
        seen_configs.add(config)
        audit = variant["audit"]
        if audit["created_on"] > audit["updated_on"] or audit["updated_on"] > today:
            errors.append(exercise_id + ": invalid audit chronology")
        reviewed = audit["reviewed_on"]
        if reviewed is not None and (reviewed < audit["created_on"] or reviewed > today):
            errors.append(exercise_id + ": invalid review date")
        if variant["status"] == "approved" and reviewed < audit["updated_on"]:
            errors.append(exercise_id + ": approval predates latest update")
    return errors

def compare_variants(left, right, attribute_ids):
    """Report known attribute matches/differences only; never infer an effect or substitute."""
    def leaves(value, path):
        if isinstance(value, dict):
            result = {}
            for key, child in value.items():
                result.update(leaves(child, path + "." + key))
            return result
        return {path: value}
    matches, differences, unknown = [], [], []
    for key in attribute_ids:
        if key not in left or key not in right:
            unknown.append(key)
            continue
        a, b = leaves(left[key], key), leaves(right[key], key)
        for path in sorted(set(a) | set(b)):
            if path not in a or path not in b:
                unknown.append(path)
            elif a[path] == b[path]:
                matches.append(path)
            else:
                differences.append(path)
    return {"same_family": left["family_id"] == right["family_id"],
            "matching_attributes": sorted(matches), "differing_attributes": sorted(differences),
            "uncompared_attributes": sorted(unknown)}

def baseline_errors(data, baseline):
    errors = []
    current = {variant["exercise_id"]: variant for variant in data["variants"]}
    for old in baseline["variants"]:
        new = current.get(old["exercise_id"])
        if new is None:
            errors.append(old["exercise_id"] + ": retain accepted IDs; retire instead of deleting")
        elif new != old:
            if new["audit"]["revision"] <= old["audit"]["revision"]:
                errors.append(old["exercise_id"] + ": increment revision for changed records")
            if new["audit"]["created_on"] != old["audit"]["created_on"]:
                errors.append(old["exercise_id"] + ": creation date is immutable")
    return errors

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--base-ref")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        data, schema = load_model(root)
        legacy = legacy_module()
        old = legacy.read_json(root / "exercises.json")
        errors = validate_model(data, schema, {item["exercise_id"] for item in old["exercises"]})
        if args.base_ref and not errors:
            result = subprocess.run(["git", "-C", str(root), "ls-tree", args.base_ref, "--", "working-model/variants.json"],
                                    capture_output=True, text=True, check=True)
            if result.stdout.strip():
                result = subprocess.run(["git", "-C", str(root), "show", args.base_ref + ":working-model/variants.json"],
                                        capture_output=True, text=True, check=True)
                errors.extend(baseline_errors(data["variants"], json.loads(result.stdout.lstrip("\ufeff"))))
    except (OSError, ValueError, KeyError, TypeError, SchemaError, subprocess.CalledProcessError) as error:
        print("FAIL: working-model validation could not complete: " + str(error), file=sys.stderr)
        return 1
    if errors:
        print("\n".join("FAIL: " + error for error in errors), file=sys.stderr)
        return 1
    print("PASS: working model v2 (" + str(len(data["families"]["families"])) +
          " family templates, " + str(len(data["variants"]["variants"])) + " variants)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
