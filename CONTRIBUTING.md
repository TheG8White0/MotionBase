# Contributing to MotionBase

MotionBase is a public exercise database independent of training methodologies. Contributions define exercises, mechanical attributes, applicability and traceable restriction assertions. Training phases, corrective programming, periodization and client prescriptions do not belong in the schema or input dictionary.

## Data and evidence

- Follow schema.json, TAXONOMY_REASONING.md and RESTRICTIONS.md. Define exact meanings, types, units, allowed values, missing-value behavior, examples and counterexamples.
- Keep family applicability explicit. Parent navigation does not inherit clinical rules. Grip and stance apply independently.
- Use synthetic examples. Include no real client identities, histories, prescriptions or medical records in files, issues, PR descriptions or screenshots.
- Use new MB-EX IDs; retain already allocated PD-EX IDs. Coordinate allocations with the owner and resolve collisions before merge. Retire accepted records rather than delete them.
- New exercise, source and restriction records start as draft. Only explicit owner review authorizes approved status and current review metadata. Agent analysis is not approval.
- A contraindication needs a scoped, source-supported assertion; distinguish precautions and review triggers. Explain population, setting, uncertainty, exceptions and re-review date. Flag clinical claims needing qualified review.
- Sources support particular assertions, not blanket safety. Identify reuse rights for imported material; citations do not permit copying proprietary text or media. External references do not determine the classification schema.
- Define context inputs as minimal typed facts with explicit meaning and units. Do not turn the input dictionary into a client medical record.

## Changes and checks

Update schema, dictionary, affected family rules, guides, validators, tests and migration/version notes together. Do not silently change accepted meanings. Changed accepted records need increased revisions and immutable creation dates.

```text
python -m pip install -r requirements-validation.txt
python -B -m unittest discover -s tests -v
python -B scripts/validate.py
python -B scripts/validate.py --base-ref origin/main
```

Python 3.13 or later is supported. A baseline ref requires Git history. The required GitHub check is named validate.

## Review and merge

Every PR requires passing checks, an agent report covering the latest head (AGENT_REVIEW.md), and the owner's personal review and explicit implementation approval. Resolve blocking findings before merge. Do not approve or merge on behalf of the owner. A checked template box or review metadata does not prove the required review occurred. The owner makes the merge decision.

GitHub review/CI protection is configured separately from repository files. Verify live settings when changing repository policy. Agent review remains a documented manual gate; no unattended review service is connected.

Data/documentation contributions use CC BY 4.0; schema/tooling/configuration use MIT. See LICENSE.md and LICENSING.md. Confirm the necessary rights and retain existing notices.
