# Contributing to PhysioData

PhysioData contains a general exercise database and supporting tooling. Only this directory is intended to become the Git repository. Client folders stay outside it.

## Contribution scope
- Submit exercise additions, corrections, sources, category changes and new attributes through pull requests.
- Include no real client names, history, assessments, workouts, contact details or identifiers, including in examples, screenshots, issues and PR descriptions.
- Use synthetic examples. A privacy scan cannot reliably identify every person or narrative.
- Supply original descriptions and traceable references. A citation alone does not permit copying proprietary text, photographs, videos, courses or manuals. State the reuse terms for imported material.
- Keep the working v2 classification independent of training frameworks. Framework-specific interpretation belongs in a separately reviewed layer. References support specific claims, not blanket exercise safety.

## Exercise records
- Forward schema development follows working-model/schema.json and TAXONOMY_REASONING.md. Define dictionary values, family applicability and precise variant attributes together. The v2 catalog is empty pending separate exercise-entry approval. Legacy v1 records continue to follow exercise.schema.json and taxonomy.json until an explicit migration. Do not fabricate missing information.
- Use a permanent PD-EX-000001 style ID. Confirm the next available ID with the maintainer; resolve concurrent ID collisions before merge.
- Retain accepted IDs. Retire obsolete variants instead of deleting them. Update audit revision and dates for changed records.
- Link regression/progression/substitution IDs and source IDs to existing records.
- Keep client loads and client-specific exclusions outside this repository.
- New records start as draft. Only the project owner's explicit review can authorize status approved and review metadata. Agent analysis alone never authorizes approval.
- Draft records can be merged as documented incomplete work; workout-generating agents must use only approved records.

## Schema and attribute changes
Explain the problem, field meaning, type, units, allowed values, null handling and effect on selection logic. Update the schema, attribute dictionary, every family applicability rule, reasoning guide, README, validator and regression tests together. Define all allowed answers or numerical reference frames, examples and counterexamples. Parent families provide navigation, not inherited rules. Grip and stance must be considered independently. Give a migration plan and version update when compatibility changes; do not silently change existing field meanings.

## Local checks
Use Python 3.13 or later. Install requirements-validation.txt in a project virtual environment, then run:
```text
python -m pip install -r requirements-validation.txt
python -B -m unittest discover -s tests -v
python -B scripts/validate.py
python -B scripts/validate_model.py
```
For an existing Git repository also run validation with --base-ref origin/main (or the actual target branch) to check retained IDs and revisions. See VALIDATION.md.

## Required reviews and merge decision
Every PR requires:
1. Passing automated validation and regression tests.
2. Agent analysis covering the latest PR head commit, recorded using AGENT_REVIEW.md. Changes after review require an updated review.
3. Personal review and explicit approval by the project owner, with blocking findings resolved.

Contributors and agents cannot approve their own work on behalf of the owner. A checked PR template box is a reminder, not evidence of a completed review. The project owner makes the final merge decision. An exercise's reviewed_by/reviewed_on fields do not replace PR review.

The agent review process is documented for manual use with Codex or Claude; no unattended agent service has been connected. Main is configured with review and CI protection; verify live settings when changing repository policy. Repository files alone do not enforce those settings.

## Licensing
See LICENSE.md and LICENSING.md. Contributions to data/written content use CC BY 4.0; contributions to the schema/tooling/configuration use MIT. By submitting, you agree to the applicable terms and confirm you have the necessary rights.
