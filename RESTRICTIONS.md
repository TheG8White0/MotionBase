# Restriction dictionary and evaluation contract

Version 3.0.0. Meanings settled for implementation on 2026-10-23. These are project data-model conventions, not a clinical guideline or training methodology.

## Record meanings

A **contraindication** records an evidence-backed restriction against selecting an exercise under specified conditions. Its action is `exclude`.

A **precaution** records an evidence-backed constraint or care instruction under specified conditions. Its action is `flag_precaution`; it does not silently modify an exercise or establish suitability.

A **review trigger** records a circumstance requiring human assessment before automatic selection. Its action is `require_review`.

There is no universal safe/unsafe exercise flag, diagnostic inference, absolute/relative shorthand without scope, or automatic clearance. Restrictions about exercise participation generally use explicit `all_exercises` scope. Other restrictions address exact families, variants or attribute conditions. Source guidance informs individual assertions; it does not control the taxonomy.

## Input dictionary

`restriction-dictionary.json` contains `schema_version` and `inputs`.

Each input has `input_id`, `label`, `definition`, `value_schema`, `units`, `examples`, and `invalid_examples` (value plus reason). Input IDs are stable snake_case names for minimal contextual facts. The schema must declare exactly one primitive type: boolean, string, number or integer. Numeric fields require named units, including a dimensionless unit where appropriate. No implicit conversion occurs.

Definitions must state what establishes a fact, what time or setting it describes and when it should be treated as unknown. Do not infer a confirmed condition from an exercise name or vague symptom. Missing or invalid values are unknown. JSON null is not a synonym for false. No personal names, histories or client records belong in the public dictionary.

## Restriction fields

- `rule_id`: permanent `MB-RULE-000001` style ID.
- `title`: human-readable rule name.
- `rule_type`: contraindication, precaution or review_trigger.
- `scope`: explicit target, described below.
- `trigger`: structured condition, described below.
- `required_inputs`: exactly the input IDs referenced by the trigger. These are potentially needed facts; boolean dominance can resolve an expression without every fact.
- `action`: the action corresponding to the rule type.
- `rationale`: source-supported reason and instruction; not executable text.
- `limitations`: population, setting, uncertainty and exclusions to the assertion.
- `source_ids`: at least one existing evidence record, even for drafts.
- `status`: draft, approved or retired.
- `audit`: created_on, updated_on, reviewed_by, reviewed_on and revision.
- `review_due_on`: scheduled re-review date. A matching overdue rule requires review instead of automatic clinical action.

An approved rule requires current review metadata and approved sources. Review metadata records content approval, not a credential check or patient clearance. AI analysis alone cannot authorize clinical content. Actual medical rules require suitable evidence and human review before publication as approved records.

## Scope

The scope object has exactly one shape:

```json
{"kind":"all_exercises"}
```

```json
{"kind":"families","family_ids":["incline_dumbbell_chest_press"]}
```

```json
{"kind":"exercises","exercise_ids":["MB-EX-000001"]}
```

```json
{"kind":"attributes","condition":{"op":"gt","field":{"namespace":"exercise","key":"bench_angle_degrees"},"value":30}}
```

IDs in scope must exist. Family scope matches exactly; it never silently expands to descendants. Attribute scope references registered exercise attributes only. It cannot read private contextual inputs. Missing exercise attributes produce unknown scope; a false trigger can still establish that a rule does not activate.

## Conditions

Predicates contain `op`, `field`, and `value`. Field is `{namespace, key}`: namespace is `exercise` for registered exercise attributes or `input` for defined context facts. The permitted operators are eq, ne, lt, lte, gt, gte, in and not_in. Comparisons use literal values; field-to-field comparison is not supported in this version.

Ordering operators require numeric fields and finite numeric boundaries. A boundary can be outside the permitted value range to express an impossible/always-false constraint. Equality and membership values must match the field vocabulary. Membership takes a nonempty list. Units come from the field definition; values are never guessed or converted.

Groups are `{op: all|any, conditions: [...]}`. Negation is `{op: not, condition: ...}`. There are at most 32 children per group, depth 12, and 256 nodes per expression. Code, arbitrary field paths, remote schema references and unrecognized operators are rejected.

- NOT unknown remains unknown.
- ALL with any false child is false; otherwise any unknown child makes it unknown.
- ANY with any true child is true; otherwise any unknown child makes it unknown.
- An unknown activation requires review. It never establishes a contraindication or clearance.

## Exercise restriction-review attributes

Every variant contains `restriction_review` with status `not_assessed` or `reviewed`, plus reviewed_by and reviewed_on. Not-assessed uses null review fields. Reviewed requires a reviewer and date covering the latest exercise update. Approved exercise records require this structural content review.

Rules remain in the restriction catalog and link to exercises through scope. We do not duplicate clinical assertions or competing rule lists inside exercise records. A consumer joins the catalogs; evaluating only the exercise file omits essential information.

## Outcome precedence and traceability

1. A matching, current, approved contraindication produces `excluded`. A retired exercise is also excluded for catalog-lifecycle reasons.
2. Otherwise, unknown relevant facts, invalid context, matching draft/overdue rules, review triggers or an unapproved/unassessed exercise produce `review_required`.
3. Otherwise, matching approved precautions produce `precaution`.
4. Otherwise, return `no_matching_rule`. This means no applicable rule activated in this snapshot, not that the activity is safe or the rule set comprehensive.

All matching approved rules are retained; a precaution cannot cancel an exclusion. Retired rules do not activate. A false condition does not create an unnecessary review solely because its record is draft. The output includes rule IDs, revisions, source IDs, rationale, missing field names and review reasons. Context values are never echoed. Consumers must honor the outcome rather than infer clearance from an empty matching_rules array.

## Synthetic implementation example

This trigger has no clinical assertion. It demonstrates a private fact activating a reviewed rule:

```json
{
  "op": "eq",
  "field": {"namespace": "input", "key": "restriction_present"},
  "value": true
}
```

Tests define a synthetic dictionary entry and source, then verify true -> excluded, false -> no_matching_rule, missing -> review_required, and NOT missing -> review_required. Synthetic test IDs are not database allocations. The shipped input, restriction, source and exercise catalogs remain empty until entries receive separate evidence/content review.

## Evidence and privacy

Source records contain source_id, title, publisher, URL, publication date if known, date checked, reuse_notes, status and audit. Sources must be public HTTP(S) references without credentials; a reference does not grant permission to copy material. Validation does not fetch or clinically verify sources.

Client-specific clinician instructions, symptoms, pain history and temporary restrictions stay private. The evaluator accepts only defined minimal facts in memory or from a private context file, does not persist them, and does not query client folders. It does not establish a diagnosis, implement emergency triage, or replace professional judgment.

As context for the distinction between participation concerns and specific exercise configurations, NHLBI advises medical consultation for chest pain or dizziness during physical activity: https://www.nhlbi.nih.gov/health/heart/physical-activity/risks. This reference has not been converted into an approved executable rule.
