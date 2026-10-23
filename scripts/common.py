"""Shared strict JSON parsing, privacy heuristics and public-file scope."""
import json
import math
from pathlib import Path
import re

PRIVATE_KEYS = {"client_name", "client_id", "patient_name", "patient_id", "date_of_birth", "dob",
                "medical_record_number", "phone", "email", "home_address", "client_history", "session_history"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
ROOT_FILES = {"README.md", "CONTRIBUTING.md", "VALIDATION.md", "AGENT_REVIEW.md", "TAXONOMY_REASONING.md",
              "RESTRICTIONS.md", "MIGRATION.md", "LICENSE.md", "LICENSING.md", "LICENSE-CODE", "LICENSE-DATA",
              "schema.json", "exercises.json", "attribute-definitions.json", "families.json",
              "restriction-dictionary.json", "restrictions.json", "sources.json",
              "requirements-validation.txt", ".gitignore", ".gitattributes"}
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(?:\+1[ -]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")
METHOD_FIELDS = {"opt_phase", "opt_phases", "opt_level", "opt_levels", "corrective_stage", "corrective_stages",
                 "corrective_targets", "programming_contexts", "training_framework", "periodization", "dosage"}

def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite JSON number")
        return number
    def invalid(value):
        raise ValueError("non-finite JSON constant: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_float=finite, parse_constant=invalid)

def walk(value, path=""):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + "/" + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + "/" + str(index))

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


def check_methodology(data):
    errors = []
    for path, value in walk(data):
        if isinstance(value, dict):
            if any(key.casefold() in METHOD_FIELDS for key in value):
                errors.append(path + ": training-methodology fields are outside the database")
            for key in ("attribute_id", "category_id", "input_id", "family_id"):
                if value.get(key, "").casefold() in METHOD_FIELDS:
                    errors.append(path + ": methodology cannot be registered as a database definition")
    return errors

def allowed_path(relative):
    if len(relative.parts) == 1:
        return relative.name in ROOT_FILES
    first = relative.parts[0]
    if first in {"scripts", "tests"}:
        return relative.suffix == ".py"
    if first == "docs":
        return relative.suffix == ".md"
    if first == ".github":
        return relative.suffix in {".md", ".yml", ".yaml"} or relative.name == "CODEOWNERS"
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
