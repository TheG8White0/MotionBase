# MotionBase v3 migration

Implemented 2026-10-23. This replaces the two active v1/v2 contracts with a single methodology-neutral v3 contract.

## Layout and compatibility

- working-model/schema.json -> schema.json; schema version 3.0.0.
- working-model/attribute-definitions.json -> attribute-definitions.json.
- working-model/families.json -> families.json.
- working-model/variants.json -> exercises.json, retaining the explicit variants array.
- Add restriction-dictionary.json, restrictions.json and sources.json.
- Retire the v1 exercise.schema.json, taxonomy.json, old methodology-dependent validator and their active tests. Historical versions remain available in Git.
- The canonical validate.py entry point now delegates to v3 validation; validate_model.py remains an equivalent direct entry point.

The old contracts have empty accepted exercise catalogs at migration. No accepted exercise IDs or medical assertions are removed. The separate first-exercise draft branch remains preserved and requires explicit migration before merge. No draft exercise is silently approved or imported by this change.

New IDs use MB-EX-000001. Existing PD-EX-000001 IDs remain permanent and valid, including the reserved first-exercise draft. Restriction IDs use MB-RULE-000001 and evidence IDs use MB-SRC-000001. Prefixes do not imply content approval.

## Removed scope

Remove OPT levels/phases, corrective stages/targets, methodology-based exercise eligibility and framework-linked dosing/programming contexts from active data/schema/validation. No replacement training system or methodology adapter is part of this database. Neutral physical descriptions remain independent of training goals.

Every exercise now requires explicit restriction-review metadata; an empty restriction catalog is not clearance. The six existing exercise attributes and five draft family templates retain their meanings. The broader proposed anatomy/equipment expansion has not been silently adopted.

Baseline validation reads either the previous working-model layout or the new root layout, preserves accepted IDs and revisions, and rejects a nonempty v1 catalog until explicit migration is provided. Restriction and source records likewise retain accepted IDs; changed records require increased revisions and unchanged creation dates.

## Project rename

The GitHub repository is renamed from TheG8White0/physiodata to TheG8White0/MotionBase without replacing its repository identity or history. The shared local folder becomes MotionBase. Git remotes, project branding and contribution links use the new name. Prior license/attribution notices remain valid and are preserved. Client folders are outside this repository.
