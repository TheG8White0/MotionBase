# PhysioData

Working classification model: **v2.0.0** | 2026-10-22

PhysioData is a public exercise classification project. Its working design separates attribute definitions, exercise families and precise exercise variants. The initial pilot covers arm/leg execution, bench inclination, fixed/rotating grip profiles, stance configuration and measured stance width. Five draft family templates illustrate applicability rules. No new exercises are added by this model.

## Working files

- [Taxonomy reasoning and entry guide](TAXONOMY_REASONING.md): definitions, possible answers, hierarchy rules, examples and limitations.
- [Working schema](working-model/schema.json): validates the combined v2 documents.
- [Attribute dictionary](working-model/attribute-definitions.json): categories, definitions, units, valid values and counterexamples.
- [Family rules](working-model/families.json): applicability, required values and permitted configurations.
- [Variant catalog](working-model/variants.json): initially empty; exercise additions require separate review.

Variant attributes remain at the top level, as in the owner-approved example:
```json
{
  "family_id": "incline_dumbbell_chest_press",
  "arm_execution": "bilateral_simultaneous",
  "bench_angle_degrees": 45,
  "grip": {
    "behavior": "rotating",
    "concentric_start": "neutral",
    "concentric_end": "pronated",
    "eccentric_behavior": "reverse"
  }
}
```
This partial illustration omits record identity and audit fields; it is not an allocated exercise or an import-ready record.

## Logic

The dictionary defines vocabulary. The family determines relevance and allowed combinations. Each variant records actual values. not_applicable and unknown are distinct; neither is inferred from absence. A variant cannot switch a required family attribute off.

Grip and stance apply independently: a bodyweight squat can omit grip, while a dumbbell squat can require both. Stance width means lateral heel-center separation in centimeters; single-leg support has no two-heel width.

Fixed grips use behavior and orientation. Rotating grips specify different concentric start/end orientations and a reverse return. Every permitted family profile is explicitly listed. Relationships can report shared attributes and precise differences without claiming physiological effects.

The model contains no training-framework or prescription fields. Additional anatomical, mechanical and equipment definitions will be added through reviewed schema work.

## Validation and contributions

```text
python -B -m unittest discover -s tests -v
python -B scripts/validate.py
python -B scripts/validate_model.py
```
Install requirements-validation.txt in a local virtual environment first. CI runs both the legacy catalog checks and the working-model checks. See [VALIDATION.md](VALIDATION.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [AGENT_REVIEW.md](AGENT_REVIEW.md).

Changes go through pull requests, automated validation, an agent report and the owner's personal review. Main is protected. Agent reports are a manual merge requirement until an actual review integration is connected.

## Legacy compatibility

The root exercises.json, exercise.schema.json and taxonomy.json retain the original v1 contract. Existing records and the separate first-exercise PR are not migrated by this change. New classification design follows the working v2 files; conversion of legacy data needs a separately reviewed migration.

Client profiles, medical history and workout logs remain outside this repository.

## Licensing

CC BY 4.0 covers data and written content; MIT covers schema and tooling. [LICENSE.md](LICENSE.md) specifies file scopes.
