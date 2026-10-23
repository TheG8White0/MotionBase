"""Synthetic restrictions exercise software semantics, not clinical assertions."""
import copy
from datetime import date
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from common import read_json, check_methodology, check_scope
from evaluate import evaluate_catalog
from validate_model import load_model, validate_model, validate_git_baseline
from safety import truth

TODAY = date.today().isoformat()

def audit():
    return {'created_on': TODAY, 'updated_on': TODAY, 'reviewed_by': 'Synthetic reviewer',
            'reviewed_on': TODAY, 'revision': 1}

def predicate(namespace='input', key='restriction_present', op='eq', value=True):
    return {'op': op, 'field': {'namespace': namespace, 'key': key}, 'value': value}

def fixture():
    data, schema = load_model()
    data = copy.deepcopy(data)
    data['families']['families'][1]['status'] = 'approved'
    data['variants']['variants'] = [{
        'exercise_id': 'MB-EX-900001', 'name': 'Synthetic exercise',
        'family_id': 'incline_dumbbell_chest_press', 'status': 'approved',
        'arm_execution': 'bilateral_simultaneous', 'bench_angle_degrees': 45,
        'grip': {'behavior': 'fixed', 'orientation': 'neutral'}, 'audit': audit(),
        'restriction_review': {'status': 'reviewed', 'reviewed_by': 'Synthetic reviewer', 'reviewed_on': TODAY}}]
    data['restriction_dictionary']['inputs'] = [{
        'input_id': 'restriction_present', 'label': 'Synthetic restriction fact',
        'definition': 'Synthetic boolean used only to verify software behavior.',
        'value_schema': {'type': 'boolean'}, 'units': None, 'examples': [True, False],
        'invalid_examples': [{'value': 'yes', 'reason': 'Use a boolean.'}]}]
    data['sources']['sources'] = [{
        'source_id': 'MB-SRC-900001', 'title': 'Synthetic reference', 'publisher': 'Synthetic publisher',
        'url': 'https://example.org/reference', 'published_on': None, 'checked_on': TODAY,
        'reuse_notes': 'Synthetic fixture, no imported clinical content.', 'status': 'approved', 'audit': audit()}]
    data['restrictions']['rules'] = [{
        'rule_id': 'MB-RULE-900001', 'title': 'Synthetic exclusion', 'rule_type': 'contraindication',
        'scope': {'kind': 'families', 'family_ids': ['incline_dumbbell_chest_press']},
        'trigger': predicate(), 'required_inputs': ['restriction_present'], 'action': 'exclude',
        'rationale': 'Synthetic software test; not a clinical recommendation.',
        'limitations': 'This assertion has no real-world clinical meaning.', 'source_ids': ['MB-SRC-900001'],
        'status': 'approved', 'audit': audit(), 'review_due_on': '2999-12-31'}]
    return data, schema

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.data, self.schema = fixture()

    def rule(self): return self.data['restrictions']['rules'][0]
    def record(self): return self.data['variants']['variants'][0]
    def errors(self): return validate_model(self.data, self.schema)
    def result(self, context=None):
        return evaluate_catalog(self.data, self.schema, 'MB-EX-900001', {} if context is None else context)

    def test_valid_contract_and_exclusion(self):
        self.assertEqual([], self.errors())
        result = self.result({'restriction_present': True})
        self.assertEqual('excluded', result['outcome'])
        self.assertEqual(['MB-SRC-900001'], result['matching_rules'][0]['source_ids'])
        self.assertEqual(1, result['rule_versions'][0]['revision'])

    def test_false_is_no_match_never_clearance(self):
        result = self.result({'restriction_present': False})
        self.assertEqual('no_matching_rule', result['outcome'])
        self.assertNotIn('safe', result)

    def test_missing_and_invalid_inputs_are_unknown(self):
        for context in ({}, {'restriction_present': None}, {'restriction_present': 1}, {'restriction_present': 'false'}):
            with self.subTest(context=context):
                result = self.result(context)
                self.assertEqual('review_required', result['outcome'])
                self.assertIn('input.restriction_present', result['missing_fields'])

    def test_not_unknown_stays_unknown(self):
        self.rule()['trigger'] = {'op': 'not', 'condition': predicate()}
        self.assertEqual('review_required', self.result()['outcome'])
        self.assertEqual('excluded', self.result({'restriction_present': False})['outcome'])

    def test_three_valued_groups(self):
        known = predicate('exercise', 'bench_angle_degrees', 'eq', 45)
        unknown = predicate()
        self.assertEqual((True, set()), truth({'op': 'any', 'conditions': [known, unknown]}, self.record(), {}))
        self.assertIsNone(truth({'op': 'all', 'conditions': [known, unknown]}, self.record(), {})[0])
        false = predicate('exercise', 'bench_angle_degrees', 'eq', 30)
        self.assertEqual((False, set()), truth({'op': 'all', 'conditions': [false, unknown]}, self.record(), {}))

    def test_precaution_and_review_trigger(self):
        for kind, action, outcome in [('precaution', 'flag_precaution', 'precaution'),
                                       ('review_trigger', 'require_review', 'review_required')]:
            self.rule().update(rule_type=kind, action=action)
            self.assertEqual(outcome, self.result({'restriction_present': True})['outcome'])

    def test_exclusion_wins_over_other_rules(self):
        second = copy.deepcopy(self.rule())
        second.update(rule_id='MB-RULE-900002', rule_type='precaution', action='flag_precaution')
        self.data['restrictions']['rules'].append(second)
        result = self.result({'restriction_present': True})
        self.assertEqual('excluded', result['outcome'])
        self.assertEqual(2, len(result['matching_rules']))

    def test_no_implicit_family_inheritance(self):
        self.rule()['scope']['family_ids'] = ['chest_press']
        self.assertEqual('no_matching_rule', self.result()['outcome'])

    def test_exercise_scope_and_global_scope(self):
        for scope in ({'kind': 'all_exercises'}, {'kind': 'exercises', 'exercise_ids': ['MB-EX-900001']}):
            self.rule()['scope'] = scope
            self.assertEqual('excluded', self.result({'restriction_present': True})['outcome'])

    def test_attribute_scope_unknown_and_false(self):
        self.rule()['scope'] = {'kind': 'attributes', 'condition': predicate('exercise', 'stance_width_cm', 'gt', 30)}
        self.assertEqual('review_required', self.result({'restriction_present': True})['outcome'])
        self.rule()['scope']['condition'] = predicate('exercise', 'bench_angle_degrees', 'lt', 30)
        self.assertEqual('no_matching_rule', self.result()['outcome'])

    def test_draft_expired_and_retired_rules(self):
        self.rule()['status'] = 'draft'
        self.assertEqual('review_required', self.result({'restriction_present': True})['outcome'])
        self.rule()['status'] = 'approved'
        self.rule()['audit']['created_on'] = '2020-01-01'
        self.rule()['review_due_on'] = '2020-01-02'
        self.assertEqual('review_required', self.result({'restriction_present': True})['outcome'])
        self.rule()['status'] = 'retired'
        self.assertEqual('no_matching_rule', self.result()['outcome'])

    def test_unreviewed_exercise_is_not_cleared_by_empty_rules(self):
        self.data['restrictions']['rules'] = []
        self.record()['status'] = 'draft'
        self.record()['restriction_review'] = {'status': 'not_assessed', 'reviewed_by': None, 'reviewed_on': None}
        self.assertEqual('review_required', self.result()['outcome'])

    def test_wrong_type_action_and_reference_fail(self):
        self.rule()['action'] = 'flag_precaution'
        self.assertTrue(self.errors())
        self.rule()['action'] = 'exclude'
        self.rule()['source_ids'] = ['MB-SRC-999999']
        self.assertTrue(self.errors())
        self.rule()['source_ids'] = ['MB-SRC-900001']
        self.rule()['scope'] = {'kind': 'families', 'family_ids': ['missing_family']}
        self.assertTrue(self.errors())

    def test_unknown_fields_wrong_values_and_operators_fail(self):
        self.rule()['trigger'] = predicate(key='missing_input')
        self.assertTrue(self.errors())
        self.rule()['trigger'] = predicate(op='gt', value=1)
        self.assertTrue(self.errors())
        self.rule()['trigger'] = predicate(value='yes')
        self.assertTrue(self.errors())
        self.rule()['trigger'] = predicate(op='eval')
        self.assertTrue(self.errors())

    def test_required_inputs_exact_and_scope_cannot_read_context(self):
        self.rule()['required_inputs'] = []
        self.assertTrue(self.errors())
        self.rule()['required_inputs'] = ['restriction_present']
        self.rule()['scope'] = {'kind': 'attributes', 'condition': predicate()}
        self.assertTrue(self.errors())

    def test_condition_size_limit(self):
        for _ in range(14):
            self.rule()['trigger'] = {'op': 'not', 'condition': self.rule()['trigger']}
        self.assertTrue(any('depth' in error for error in self.errors()))

    def test_extreme_depth_rejected_before_recursive_schema_check(self):
        for _ in range(300):
            self.rule()['trigger'] = {'op': 'not', 'condition': self.rule()['trigger']}
        self.assertTrue(any('depth' in error for error in self.errors()))

    def test_baseline_reads_both_historical_catalogs(self):
        import json
        def git_result(command, **kwargs):
            if 'ls-tree' in command:
                return SimpleNamespace(stdout='working-model/variants.json\nexercises.json\n')
            body = ({'variants': []} if command[-1].endswith('working-model/variants.json') else
                    {'exercises': [{'exercise_id': 'PD-EX-000001'}]})
            return SimpleNamespace(stdout=json.dumps(body))
        with patch('validate_model.subprocess.run', side_effect=git_result):
            self.assertTrue(any('Nonempty v1' in error for error in validate_git_baseline(ROOT, 'base', self.data)))

    def test_baseline_preserves_new_rule_and_source_ids(self):
        import json
        previous_rule = copy.deepcopy(self.rule())
        previous_source = copy.deepcopy(self.data['sources']['sources'][0])
        old = {'exercises.json': {'variants': []}, 'restrictions.json': {'rules': [previous_rule]},
               'sources.json': {'sources': [previous_source]}}
        def git_result(command, **kwargs):
            if 'ls-tree' in command:
                return SimpleNamespace(stdout='\n'.join(old))
            return SimpleNamespace(stdout=json.dumps(old[command[-1].split(':', 1)[1]]))
        self.data['restrictions']['rules'] = []
        self.data['sources']['sources'] = []
        with patch('validate_model.subprocess.run', side_effect=git_result):
            errors = validate_git_baseline(ROOT, 'base', self.data)
        self.assertTrue(any('MB-RULE-900001' in error for error in errors))
        self.assertTrue(any('MB-SRC-900001' in error for error in errors))

    def test_node_and_child_limits(self):
        node = predicate()
        self.rule()['trigger'] = {'op': 'all', 'conditions': [node] * 33}
        self.assertTrue(any('32 children' in error for error in self.errors()))
        self.rule()['trigger'] = {'op': 'all', 'conditions': [
            {'op': 'all', 'conditions': [node] * 32} for _ in range(9)]}
        self.assertTrue(any('256' in error for error in self.errors()))

    def test_sources_need_review_and_public_provenance(self):
        source = self.data['sources']['sources'][0]
        source['status'] = 'draft'
        self.assertTrue(self.errors())
        source['status'] = 'approved'
        source['url'] = 'https://localhost/reference'
        self.assertTrue(self.errors())
        source['url'] = 'https://example.org/reference'
        source['audit']['reviewed_on'] = None
        self.assertTrue(self.errors())

    def test_input_schemas_examples_units_and_refs(self):
        entry = self.data['restriction_dictionary']['inputs'][0]
        entry['value_schema'] = {'$ref': 'https://example.org/schema'}
        with patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network access')) as fetch:
            self.assertTrue(self.errors())
            fetch.assert_not_called()
        entry['value_schema'] = {'type': 'number'}
        self.assertTrue(any('units' in error for error in self.errors()))

    def test_result_does_not_echo_private_values(self):
        result = self.result({'unregistered_private_fact': 'SYNTHETIC_PRIVATE_VALUE'})
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', str(result))
        self.assertEqual('review_required', result['outcome'])

    def test_methodology_definitions_rejected(self):
        self.assertTrue(check_methodology({'inputs': [{'input_id': 'opt_phase'}]}))
        self.assertTrue(check_methodology({'corrective_targets': []}))

    def test_strict_json_nonfinite_and_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'input.json'
            for body in ('{"x": 1, "x": 2}', '{"x": NaN}', '{"x": 1e999}'):
                path.write_text(body, encoding='utf-8')
                with self.assertRaises(ValueError): read_json(path)

    def test_repository_scope_excludes_old_contract_and_client_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'taxonomy.json').write_text('{}', encoding='utf-8')
            self.assertTrue(check_scope(root))
            (root / 'taxonomy.json').unlink()
            (root / 'client-notes.txt').write_text('synthetic', encoding='utf-8')
            self.assertTrue(check_scope(root))

    def test_evaluator_rejects_invalid_catalog_and_unknown_exercise(self):
        with self.assertRaises(ValueError): evaluate_catalog(self.data, self.schema, 'MB-EX-999999', {})
        self.rule()['action'] = 'unsupported'
        with self.assertRaises(ValueError): self.result()

if __name__ == '__main__':
    unittest.main()
