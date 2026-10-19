# PhysioData shared exercise database

Approved structure v1.0.0 | 2026-10-19

This folder is shared by every client. It contains the database structure and one draft exercise record for coach review; no client workout prescriptions have been added. The initial taxonomy is approved and can evolve through reviewed changes.

PhysioData is the project name; Delta Fitness is its initial coaching use case.

## Files

- exercises.json: exercise records; currently one draft, PD-EX-000001 (standing band shoulder external rotation with the elbow at the side). Draft records are excluded from workout generation.
- exercise.schema.json: exact field names, data types, allowed values, and draft/approval requirements (JSON Schema 2020-12).
- taxonomy.json: readable categories, subcategories and framework sources.

JSON supports multiple categories and structured equipment/dosage requirements without duplicating exercise identity. Client workout exports can remain CSV. No database server or installation is required.

## Categories and subcategories

1. OPT level and phase
   - Stabilization: 1 / Stabilization Endurance.
   - Strength: 2 / Strength Endurance; 3 / Muscular Development / Hypertrophy; 4 / Maximal Strength.
   - Power: 5 / Power.
2. Corrective Exercise Continuum
   - Inhibit; Lengthen; Activate; Integrate.
   - Track separately from OPT phase. A client can have an OPT phase and corrective work together. Corrective use requires coach-documented assessment findings; do not classify a client automatically.
3. Session component
   - Self-myofascial release; flexibility; mobility; core; balance; resistance; plyometric; speed/agility/quickness; cardiorespiratory; movement preparation.
4. Anatomical target
   - Foot/ankle; knee; hip; LPHC; thoracic spine; cervical spine; shoulder/scapula; elbow; wrist/hand; whole body.
   - Within each: specific joints, joint actions, primary and secondary muscles.
5. Corrective purpose
   - Mobility/range of motion; motor control; balance/proprioception; joint stability; strength capacity; soft tissue preparation.
   - Combine with anatomical target, e.g. shoulder/scapula + joint stability + shoulder external rotation. These are selection intentions, not diagnoses.
6. Movement pattern
   - Squat; hinge; lunge; step; horizontal/vertical push; horizontal/vertical pull; carry; rotation; anti-rotation; anti-extension; anti-lateral-flexion; gait; balance; jump/land; throw; locomotion; isolated joint action; stretch; self-myofascial release.
7. Execution and demands
   - Plane: sagittal; frontal; transverse (multiple allowed).
   - Contraction: isometric; concentric; eccentric; not applicable. Dynamic/isotonic exercise can include concentric and eccentric actions; body position is a separate field.
   - Bilateral; unilateral; alternating; not applicable.
   - Single-joint; multi-joint; not applicable.
   - Open; closed; mixed kinetic chain; not applicable.
   - Position, external support, stable/unstable surface, impact, controlled/rapid lateral movement, and ballistic demand.
8. Equipment
   - Exact required item(s), quantity, attachment/specification, optional items, and setup needs.
   - All required items must be available. Different equipment can require a separately identified variant; do not silently treat substitutions as equivalent.

These are overlapping filter dimensions. Each exercise exists once and can have multiple contexts. Do not create five duplicate copies of an exercise for five OPT phases.

## Exercise attributes

### Identity and review
exercise_id; name; aliases; family; status.
audit: created_on; updated_on; reviewed_by; reviewed_on; revision; notes.

### Classification
classification: training_components; body_regions; joints; joint_actions; primary_muscles; secondary_muscles; movement_patterns; planes; contraction_types; limb_mode; joint_scope; kinetic_chain; position; support_level; surface; impact_level; lateral_speed; ballistic.

### Corrective targets
corrective_targets: body_region; focus; selection_basis. Use an empty list for an exercise with no corrective purpose.

### Equipment and coaching
equipment: required (name, quantity, specification); optional; setup_notes.
instructions: setup; execution; cues; common_errors.
load_tracking: metric; unit_options; load_basis; notes.

### Programming contexts
programming_contexts: context_id; opt_phase; corrective_stage; session_role; selection_criteria; dosage; source_ids.

Every context must specify an OPT phase, corrective stage, or both. A phase-2 strength/stabilization pairing or phase-5 strength/power pairing is represented through separate context roles; the actual pairing is assembled in the client's proposed workout.

dosage contains:
- dose_type: repetitions, hold_seconds, work_seconds, or distance_meters.
- sets; repetitions; hold_seconds; work_seconds; distance_meters: min/max ranges.
- count_basis: total, per_side, per_limb, or not_applicable.
- intensity_measure: rpe_rir, rpe_0_10, percent_1rm, technique_quality, movement_quality_velocity, or not_applicable.
- rpe; rir; percent_1rm: min/max ranges; only the applicable measurement is filled.
- tempo: eccentric_seconds, hold_after_eccentric_seconds, concentric_seconds, hold_after_concentric_seconds, and intent.
- rest_seconds: min/max; estimated_setup_seconds; estimated_block_seconds; notes.

RPE 9 approximately corresponds to 1 RIR for applicable resistance work. Do not automatically assign RPE/RIR to stretching, inhibition, balance, or power work. The coach chooses the relevant quality or effort measure and dosing for each context. No generic dosing ranges have been prefilled.

### Selection and references
selection: demands; precautions (restriction_tag, instruction, source_ids); regression_ids; progression_ids; substitution_ids.
sources: source_id; type; title; url; locator; checked_on; supports.

Coach practice is a valid labeled source. Never label a coach modification as NASM guidance or treat one reference as support for every field.

## ID and variant rules

- IDs follow the PD-EX-000001 format. PD-EX-000001 is assigned to the first draft exercise; check exercises.json before allocating another ID.
- Assign the next unused number when adding a real exercise. For concurrent contributions, the maintainer confirms a unique ID before merging. IDs never change or get reused once accepted.
- Phase, corrective target, and equipment categories are stored in fields, not encoded in IDs.
- A meaningful change in equipment, support, stance, contraction, or range that needs separate tracking gets a new variant ID and a shared family label.
- Left/right performance uses the same exercise ID; side and any side-specific restrictions are recorded in the client prescription/log.
- Changes to sets, reps, load or target effort do not create a new exercise ID.
- Retire records instead of deleting exercise IDs referenced by client history.

## Completeness and validation

- Draft records require exercise_id, name and status; omitted information is unknown, never assumed safe or available.
- Approved records require all attribute groups, a nonempty programming context, sources, coaching instructions, and coach review identity/date.
- JSON null means unknown or not applicable as explained by the field; [] means intentionally no entries. Never put zero in place of an unknown load or dose.
- In a usable context, sets must be positive integers and the selected dose must have positive values. Nonapplicable dose/effort ranges use null endpoints. Where both endpoints exist, min must not exceed max.
- Only rpe_rir contexts use RIR; use the chosen intensity measure consistently. Tempo/effort fields irrelevant to a context remain null.
- Sets/reps are whole numbers. Durations use seconds, distances meters. Every client load has a unit and load basis; band and machine settings require identifying equipment.
- Exercise IDs must be globally unique. Context and source IDs must be unique within their exercise. All linked exercise IDs and source IDs must resolve; links cannot point to the same exercise.
- Controlled values must match taxonomy.json. Update taxonomy and the schema together when expanding categories.
- JSON Schema checks field shapes and enums. scripts/validate.py additionally checks unique keys, linked IDs, min/max ordering, dose/intensity consistency and public repository scope; see VALIDATION.md.

## How the agent uses this database

1. Read the shared coaching methodology once created, then client notes, latest assessments, restrictions, goals and dates, progression history, and the requested session count.
2. Consider approved exercise records and matching phase/stage contexts only. Missing review or suitability information requires coach review.
3. Apply documented client exclusions, pain history, equipment requirements and movement demands. A database tag does not override a restriction.
4. Use client performance to propose doses; preserve units, side, tempo and equipment identity. Do not compare loads across different exercise variants or machine/band settings as if equivalent.
5. Preserve the coach's pain exclusion until documented reassessment and explicit reintroduction approval. The coach determines causes of missed repetitions and phase progression.
6. Save proposed workouts for coach review. Do not make them active until the coach approves them.

A later root agent entry file and methodology skill will establish the full reading order. This database folder alone does not configure Codex or Claude automatically.

## Client-specific information stays in client folders

Medical/surgical history; actual assessment findings; goals and dates; active phase and plan dates; schedule; available equipment; pain exclusions; clinician restrictions; completed sets/reps/load/RPE/RIR; session notes; workout approvals. The shared database contains no client-specific rules or records.

## Framework references

NASM defines the five OPT phases and the Inhibit, Lengthen, Activate, Integrate stages. All additional database dimensions and field names are Delta Fitness design proposals.

- OPT model: https://www.nasm.org/certified-personal-trainer/the-opt-model
- Corrective Exercise Continuum: https://www.nasm.org/resource-center/blog/recovery/a-guide-to-nasms-corrective-exercise-continuum

Both checked 2026-10-19. These references establish framework terminology; they do not verify exercise-specific entries, which will require their own references.



## Contributions, reviews and validation

All changes go through pull requests, automated checks, an agent review of the latest head, and personal review by the project owner. Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENT_REVIEW.md](AGENT_REVIEW.md), and [VALIDATION.md](VALIDATION.md). The validator now implements semantic checks as well as JSON Schema checks. GitHub CI is prepared in .github/workflows/validate.yml; review enforcement requires repository settings after creation.

PhysioData uses CC BY 4.0 for data and written content, and MIT for tooling and the schema. See [LICENSE.md](LICENSE.md) for exact scopes and attribution, and [LICENSING.md](LICENSING.md) for contribution terms.
