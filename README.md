# MotionBase

MotionBase is a public, methodology-neutral exercise database. Version **3.0.0** defines exercise attributes, family applicability and independently sourced restriction rules. Movement descriptions do not prescribe training phases, corrective sequences, periodization or client workloads.

## One active contract

- `schema.json`: JSON Schema 2020-12 for the combined documents.
- `attribute-definitions.json`: category hierarchy, six initial exercise attributes, units and entry examples.
- `families.json`: five draft family templates and explicit applicability rules.
- `exercises.json`: exercise variants and their restriction-review state.
- `restriction-dictionary.json`: precisely typed contextual input definitions.
- `restrictions.json`: contraindication, precaution and review-trigger rules.
- `sources.json`: traceable evidence and review metadata.

The exercise, restriction, input and source catalogs are initially empty. Family templates are classification scaffolding, not approved exercise records. The broader anatomy/equipment taxonomy remains a separate design proposal; this migration does not claim to implement it.

The schema validates the logical object assembled from these files. Use the validator to load and check them together; validating an individual file against the entire bundle is not equivalent.

## Restriction meanings

- **Contraindication:** exclude selection when the documented condition is established for the specified scope.
- **Precaution:** flag the documented constraint when its condition is established.
- **Review trigger:** require human review before automatic selection continues.

Conditions evaluate to true, false or unknown. Results are `excluded`, `review_required`, `precaution`, or `no_matching_rule`. None constitutes medical clearance. A draft exercise or an unassessed restriction profile requires review even when no restriction rules are present.

See [RESTRICTIONS.md](RESTRICTIONS.md) for all fields, evaluation semantics and a synthetic example; [TAXONOMY_REASONING.md](TAXONOMY_REASONING.md) for exercise definitions; and [MIGRATION.md](MIGRATION.md) for the transition from the earlier contracts.

## Validation and use

Install `requirements-validation.txt` in a project virtual environment, then run:

```text
python -B -m unittest discover -s tests -v
python -B scripts/validate.py
python -B scripts/validate.py --base-ref origin/main
```

The optional evaluator accepts a private file containing only declared input IDs:

```text
python -B scripts/evaluate.py --exercise-id MB-EX-000001 --context <private-context-file>
```

That command requires an existing exercise; the initial catalog contains none. It validates the entire snapshot before evaluation, outputs explanations without raw context values, and never writes context to the repository. It does not generate workouts or diagnose conditions.

Public contributions require automated checks, an agent report and the owner's personal review. New content remains draft until explicitly approved. [CONTRIBUTING.md](CONTRIBUTING.md) and [VALIDATION.md](VALIDATION.md) describe the process and limitations.

## Identity and licenses

Repository: https://github.com/TheG8White0/MotionBase. New exercise IDs use `MB-EX-000001`; existing `PD-EX-000001` identifiers remain valid and must not be reassigned. Medical and client records remain outside the repository.

Data and documentation use CC BY 4.0. Schema and tooling use MIT. Existing attribution notices remain valid; see [LICENSE.md](LICENSE.md).
