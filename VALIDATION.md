# MotionBase validation

Run the tests and canonical validator shown in README.md. The GitHub validate job runs both and checks the actual PR-base commit. It uses pinned actions, read-only contents permission, no model credentials and no client data.

## Enforced checks

- Strict JSON: duplicate keys, non-finite constants and float overflow are rejected.
- Fixed v3 bundle shape, registered attributes, dictionary/schema agreement, examples and counterexamples.
- Unique IDs, valid parent links, acyclic category/family hierarchies and complete explicit family applicability.
- Grip profiles, inclination ranges, independent leg/stance geometry and single-leg width consistency.
- Duplicate configurations treat numerically equal 45 and 45.0 identically without rounding distinct values.
- Exercise review/audit dates, restriction-review completeness and approved family requirements.
- Restriction/source/input references, rule/action agreement, typed operators and comparison values, numeric units and exact referenced-input lists.
- Explicit scopes, exercise-only attribute selectors and bounded expressions (depth 12, 256 nodes, 32 children/group).
- Approved rule/source review metadata, date order, public reference URL structure and source attribution fields.
- Methodology fields and known methodology identifier registrations are prohibited. This guard does not replace review of renamed or indirect concepts.
- Public-file allowlist and privacy heuristics. Legacy contracts and client files are outside active public scope.
- Baseline preservation of exercise/rule/source IDs and revisions, including the old working-model path. Nonempty v1 data requires explicit migration.

Schema recursion uses bundled local references only; dictionary/family/input inline schemas reject references. A no-retrieval schema registry prevents remote schema fetching. Validation performs no live source fetching.

## Evaluator checks

The public evaluate_catalog function validates the complete snapshot before applying rules. Input types are checked before comparison. Missing/invalid facts remain unknown under negation. Relevant draft/overdue rules and unassessed exercises require review. Exclusions dominate precaution/review outcomes, all matching approved rules are returned, and no-match never becomes safe. Raw context values are not echoed.

CLI success means evaluation completed; consumers must inspect outcome. Unknown exercise IDs or invalid catalogs fail with a nonzero exit code. Evaluator context must stay outside the public repo.

## Limits

Passing checks does not establish clinical truth, completeness, source reuse permission, reviewer qualifications, approval authenticity or exercise suitability. Free-text privacy checks are heuristic. Review the latest code diff and sources personally; tests modified by an author do not independently establish correctness. The initial catalogs contain no approved clinical rules.

Main should retain required pull requests, the validate check, stale-review dismissal, code-owner review and discussion resolution. Repository renaming does not authorize bypassing these protections.
