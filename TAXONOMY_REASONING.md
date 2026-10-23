# Taxonomy reasoning and contributor dictionary

Active contract: 3.0.0 | consolidated 2026-10-23

This document explains the family/attribute/variant design approved by the project owner. The executable contract is schema.json. This is an initial classification foundation, not a complete anatomy or exercise ontology. The current pilot defines six attributes and five draft family templates; it contains no exercise variants.

## Three layers

1. attribute-definitions.json defines categories and reusable attributes. Each attribute has a definition, units, a value_schema, meanings for its vocabulary, valid examples and counterexamples.
2. families.json defines exercise groupings, optional parent families, applicability and admissible configurations.
3. exercises.json holds actual exercise records with permanent IDs and explicit values selected from those rules.

Names and IDs are labels, not classification parsers. An agent must use structured fields, not infer grip or inclination from an exercise name.

## Category hierarchy

The initial categories are:
- Execution -> Arm coordination and Leg coordination.
- Setup -> Bench geometry and Stance geometry.
- Hand configuration -> Grip profile.

A category parent groups definitions. It does not imply a clinical progression. Category and family hierarchies are separate; an attribute's category does not determine an exercise's family. More anatomical, equipment and movement categories require reviewed additions with the same definitions and examples.

Category fields:
- category_id: stable snake_case identifier.
- parent_category_id: another category ID, or null for a root.
- label: readable category name.
- definition: what membership means.

Missing parents, repeated IDs and hierarchy cycles are invalid.

## Attribute dictionary fields

- attribute_id: stable field name used in variant records.
- category_id: the category containing this attribute.
- label: readable name.
- definition: precise meaning and reference frame.
- units: unit name, or null when not a measurement.
- missing_value_policy: currently omit_unknown.
- value_schema: the permitted JSON shape and values.
- value_definitions: explanations of vocabulary and numerical conventions.
- examples: valid values.
- invalid_examples: invalid values paired with reasons.

The inline schema keyword subset is: type, enum, const, minimum, maximum, exclusiveMinimum, exclusiveMaximum, multipleOf, minLength, maxLength, pattern, format, required, properties, additionalProperties, items, minItems, maxItems, uniqueItems, minProperties, maxProperties, allOf, anyOf, oneOf, not, if, then, else, dependentRequired, dependentSchemas, propertyNames, description and title. The bundle declares the fixed 2020-12 dialect; reference keywords are not supported.

Dictionary value schemas must match their corresponding variant-schema fields exactly. Examples and counterexamples are checked automatically. Inline rules use a documented subset of JSON Schema; remote references and unknown keywords are rejected rather than fetched or silently ignored. Extend the validator through a reviewed PR if additional schema vocabulary is needed.

## Arm execution

Field: arm_execution. Values:
- bilateral_simultaneous: both arms perform the repetition together.
- bilateral_alternating: both arms participate but alternate effort phases.
- unilateral: one arm performs the recorded repetition.

This records execution, not implement count. Two available dumbbells do not prove simultaneous bilateral use. The incomplete label bilateral is not accepted because it omits timing. Families may permit only a subset of these values.

## Leg execution and stance geometry

Field: leg_execution. The same timing vocabulary as arm_execution applies to working legs: bilateral_simultaneous, bilateral_alternating, unilateral. A balance/support leg is not necessarily a working leg. Do not infer execution from equipment count or stance geometry.

Field: stance_configuration. Possible values:
- bilateral_aligned: two supporting feet with heel centers aligned fore-aft. This does not mean toes must point parallel.
- bilateral_staggered: two supporting feet with one heel center ahead of the other.
- single_leg: one supporting foot.

Field: stance_width_cm. A number greater than or equal to zero, in centimeters. Measure the lateral separation between heel centers, projected onto the horizontal left-right axis perpendicular to the exerciser's forward axis at the family's named setup position. The squat templates use the upright standing setup immediately before descent and maintain that foot placement. This is a project-specific recording convention. It is not the diagonal distance between heels, distance between foot edges, toe spacing, or fore-aft stride length. Zero describes heel centers on the same fore-aft line; missing does not mean zero.

Record an intentionally specified or measured setup. "Wide", "normal", "hip-width" and "shoulder-width" do not provide an exact value and have no automatic conversion. No universal width cutoffs are asserted. A single-leg stance has no two-heel width: stance_width_cm must be omitted and the family must mark it not applicable. Dynamic changes in foot placement, toe angles, side differences and normalized body-dimension measurements require separately defined attributes before entry; do not overload width.

These attributes are independent. A bodyweight squat without hand support can require leg execution, stance configuration and stance width while grip is not applicable. A side-held dumbbell squat can require grip and those same lower-body attributes together. There is no global lower-body-implies-no-grip rule. Upper-body families may classify supporting foot geometry in a future explicit extension; the press pilot currently marks those applicability decisions unknown. Unresolved is not the same as inherently irrelevant.

## Bench backrest angle

Field: bench_angle_degrees. Numeric coordinate range: -90 through 90 degrees.
- 0: horizontal.
- Positive: backrest rises above horizontal.
- Negative: backrest declines below horizontal.

This measures the backrest, not the seat, humeral position, torso arch, or an angle relative to the client's body. Record the nominal angle set or measured; do not silently round 30 to 45. A family can constrain this coordinate range. The pilot incline family requires an angle greater than 0 and less than 90.

A number's acceptance by a schema is not a statement of exercise suitability. Family-specific setup meaning must be reviewed. Missing angle is unknown, not zero.

## Grip profiles

Field: grip. Grip refers here to forearm orientation, not grip width, finger closure, wrist flexion or palm direction relative to the room. Those may become separately defined attributes later.

Orientation vocabulary:
- pronated: forearm in pronation.
- neutral: orientation between pronation and supination.
- supinated: forearm in supination.

Prone and supine describe body position; they are not orientation values in this field.

Fixed profile:
```json
{"behavior":"fixed","orientation":"neutral"}
```

A fixed profile supplies orientation only. It does not require fictitious concentric/eccentric fields for an exercise without those phases.

Rotating profile:
```json
{
  "behavior":"rotating",
  "concentric_start":"neutral",
  "concentric_end":"pronated",
  "eccentric_behavior":"reverse"
}
```

The orientation transition is defined during the concentric effort phase of the named exercise; reverse means the return retraces that orientation path. Start and end must differ. Fixed and rotating fields cannot be mixed. Unknown, complex, asymmetric, or non-reversing profiles are not approximated by a supported profile; propose a reviewed extension.

The pilot lists six profiles: fixed pronated, fixed neutral, fixed supinated, pronated-to-neutral, neutral-to-pronated, and supinated-to-neutral, with reverse return for rotating profiles. These are draft classification configurations from the owner's example. They are not independently approved exercise records or physiological claims.

## Applicability and family rules

A supplied stance width also requires an explicit two-foot stance_configuration. A family limited to single_leg must mark width not_applicable; required width needs a required configuration admitting two-foot support. These cross-attribute rules apply even when the variant catalog is empty. Other combinations still require contributor and owner review; this is not a general satisfiability solver for arbitrary schemas.

Every family explicitly declares a rule for every registered attribute:
- applicability: applicable, not_applicable, or unknown.
- required: whether an applicable attribute must be supplied.
- allowed_values: a nonempty list narrowing the global vocabulary, or null for no list restriction.
- value_constraints: an optional further inline schema, or null.
- reason: why the rule applies to that family.

applicable + required true: the variant must supply a valid value.
applicable + required false: omission is allowed, but a supplied value is validated.
not_applicable: the variant must omit the field.
unknown: applicability has not been resolved; the variant must omit the field.

not_applicable and unknown cannot require a value or declare allowed values/constraints. Omission is never rewritten as false, neutral, zero or a matching attribute. Applicability is governed by the family, not an arbitrary switch on the variant.

All supplied values must satisfy both the global definition and every family restriction. A list and a numerical/object constraint narrow one another; neither overrides the global definition. New allowed combinations require a reviewed family change.

## Families and hierarchy

Family fields: family_id, parent_family_id, name, status, definition, attribute_rules.

The pilot has chest_press and squat as broad parents. Draft children are incline_dumbbell_chest_press, bilateral_bodyweight_squat and bilateral_side_held_dumbbell_squat. The squat children are synthetic classification templates demonstrating applicability, not exercise catalog entries. The press child currently permits bilateral simultaneous execution only, matching the owner's pilot. A future extension can add unilateral or alternating configurations after review.

Parent relationships organize navigation only. There is no hidden rule inheritance, automatic muscle assignment or implicit merging of field values. Each family's applicability rules are complete and explicit. This avoids a child silently receiving a contradictory default from a parent. A future inheritance mechanism would require a separate design and tests.

## Variants, IDs and review

Each record contains exercise_id, name, family_id, status, audit, and relevant top-level attribute values. This preserves the approved example's arm_execution, bench_angle_degrees and grip layout.

Existing PD-EX-000001 identifiers remain permanent; new allocations use MB-EX-000001. Catalog entries must be unique by both ID and family/attribute configuration. Numerically equal values such as 45 and 45.0 identify the same configuration; distinct measured values are not rounded together. Synthetic test IDs are not allocations. Previously allocated IDs cannot be reassigned during migration.

Status can be draft, approved or retired. An approved variant requires an approved family and current review metadata. Schema validity does not establish approval authenticity, equipment safety or client eligibility. No actual variants are inserted by this schema change.

Audit fields: created_on, updated_on, reviewed_by, reviewed_on, revision. Dates use YYYY-MM-DD. Approval must cover the latest update. Baseline checks prevent silent ID deletion and require revision increases for changed accepted records.

## Relationships

compare_variants reports same_family, matching_attributes, differing_attributes and uncompared_attributes. It compares actual known values, including nested grip fields. Omitted values are uncompared, never shared evidence. Different families can share known attributes without being declared equivalent.

For two otherwise matching fixed-grip examples, neutral versus pronated is a difference at grip.orientation. No score, progression, substitution, muscle-effect estimate or clinical suitability is inferred. Such assertions need separately defined relationships and evidence later.

## Scope and compatibility

MotionBase is a methodology-neutral exercise database. Training-framework fields, phase eligibility, corrective programming, dosage, periodization and client prescriptions are excluded rather than deferred to an adapter. The old contracts are replaced by the single v3 contract described in MIGRATION.md.

Every variant also contains restriction_review (not_assessed or reviewed, with reviewer/date). This is content-review metadata, not an anatomical attribute or medical clearance. Scoped clinical assertions remain in restrictions.json and link through explicit targets. RESTRICTIONS.md defines their vocabulary, sources and true/false/unknown evaluation.

The six exercise attributes remain an initial foundation. The broader proposed movement/anatomy/equipment dictionary is separate work, not silently implemented here. No actual exercise or clinical rule is added by this migration. The bundle uses named local JSON Schema references for recursive rule conditions; inline attribute/input/family schemas still reject references.

## References

The schema uses JSON Schema 2020-12. Definitions here are project-authored classification conventions.
- https://json-schema.org/understanding-json-schema/reference/conditionals
- https://json-schema.org/understanding-json-schema/structuring
