"""Typed restriction validation and three-valued evaluation; no diagnostic inference."""
from datetime import date
import ipaddress
import math
from urllib.parse import urlparse
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

ACTIONS = {'contraindication': 'exclude', 'precaution': 'flag_precaution', 'review_trigger': 'require_review'}
NUMERIC = {'lt', 'lte', 'gt', 'gte'}
PREDICATES = {'eq', 'ne', 'in', 'not_in'} | NUMERIC

def preflight_condition_limits(data):
    """Bound untrusted condition trees iteratively before recursive JSON Schema checks."""
    if not isinstance(data, dict) or not isinstance(data.get('restrictions'), dict):
        return []
    rules = data['restrictions'].get('rules')
    if not isinstance(rules, list):
        return []
    errors = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        roots = [rule.get('trigger')]
        scope = rule.get('scope')
        if isinstance(scope, dict) and scope.get('kind') == 'attributes':
            roots.append(scope.get('condition'))
        for root in roots:
            stack, count = [(root, 0)], 0
            while stack:
                node, depth = stack.pop()
                count += 1
                if depth > 12 or count > 256:
                    errors.append('restriction ' + str(index) + ': condition exceeds depth 12 or node count 256')
                    break
                if isinstance(node, dict):
                    if node.get('op') == 'not':
                        stack.append((node.get('condition'), depth + 1))
                    elif node.get('op') in {'all', 'any'} and isinstance(node.get('conditions'), list):
                        if len(node['conditions']) > 32:
                            errors.append('restriction ' + str(index) + ': group exceeds 32 children')
                            break
                        stack.extend((child, depth + 1) for child in node['conditions'])
    return errors

def fits(schema, value):
    return Draft202012Validator(schema, format_checker=FormatChecker(), registry=Registry()).is_valid(value)

def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and (not isinstance(value, float) or math.isfinite(value))

def condition_errors(node, exercise_fields, inputs, scope_only=False, depth=0, budget=None):
    """Return errors and referenced input IDs; the bundle already checks JSON shape."""
    budget = [0] if budget is None else budget
    budget[0] += 1
    if depth > 12 or budget[0] > 256:
        return ['condition exceeds depth 12 or node count 256'], set()
    op = node['op']
    if op in {'all', 'any', 'not'}:
        nodes = [node['condition']] if op == 'not' else node['conditions']
        errors, references = [], set()
        for child in nodes:
            found, refs = condition_errors(child, exercise_fields, inputs, scope_only, depth + 1, budget)
            errors.extend(found)
            references.update(refs)
        return errors, references
    namespace, key = node['field']['namespace'], node['field']['key']
    references = {key} if namespace == 'input' else set()
    if scope_only and namespace != 'exercise':
        return ['attribute scope can reference exercise attributes only'], references
    definitions = exercise_fields if namespace == 'exercise' else inputs
    if key not in definitions:
        return ['unknown ' + namespace + ' field ' + key], references
    definition = definitions[key]['value_schema']
    value = node['value']
    if op in NUMERIC:
        if definition.get('type') not in {'number', 'integer'} or not numeric(value):
            return ['numeric operator requires a numeric field and finite numeric comparison value'], references
        # A boundary may lie outside a permitted range: x < 0 still has a meaning.
        return [], references
    values = value if op in {'in', 'not_in'} else [value]
    if not isinstance(values, list) or not values:
        return ['membership operator requires a nonempty list'], references
    if any(not fits(definition, candidate) for candidate in values):
        return ['comparison value does not match field type or permitted vocabulary'], references
    return [], references

def audit_errors(item, label):
    audit = item['audit']
    today = date.today().isoformat()
    errors = []
    if audit['created_on'] > audit['updated_on'] or audit['updated_on'] > today:
        errors.append(label + ': invalid audit chronology')
    reviewed = audit['reviewed_on']
    if reviewed is not None and (reviewed < audit['created_on'] or reviewed > today):
        errors.append(label + ': invalid review date')
    if item['status'] == 'approved' and (not audit['reviewed_by'] or reviewed is None or reviewed < audit['updated_on']):
        errors.append(label + ': approved content requires current human review metadata')
    return errors

def validate_safety(data, schema):
    from validate_model import restricted_schema_errors
    errors = []
    exercise_fields = {a['attribute_id']: a for a in data['attribute_definitions']['attributes']}
    inputs = {}
    for definition in data['restriction_dictionary']['inputs']:
        key = definition['input_id']
        if key in inputs:
            errors.append('duplicate restriction input ID ' + key)
        inputs[key] = definition
        value_schema = definition['value_schema']
        found = restricted_schema_errors(value_schema, key)
        errors.extend(found)
        if found:
            inputs.pop(key, None)
            continue
        if value_schema.get('type') not in {'boolean', 'number', 'integer', 'string'}:
            errors.append(key + ': input must have one explicit primitive non-null type')
            inputs.pop(key, None)
            continue
        if value_schema.get('type') in {'number', 'integer'} and definition['units'] is None:
            errors.append(key + ': numeric input needs explicit units, including a dimensionless unit when appropriate')
        if any(not fits(value_schema, item) for item in definition['examples']):
            errors.append(key + ': invalid positive input example')
        if any(fits(value_schema, item['value']) for item in definition['invalid_examples']):
            errors.append(key + ': invalid input example is actually valid')
    families = {item['family_id']: item for item in data['families']['families']}
    exercises = {item['exercise_id']: item for item in data['variants']['variants']}
    sources = {}
    today = date.today().isoformat()
    for source in data['sources']['sources']:
        key = source['source_id']
        if key in sources:
            errors.append('duplicate source ID ' + key)
        sources[key] = source
        errors.extend(audit_errors(source, key))
        parsed = urlparse(source['url'])
        host = parsed.hostname or ''
        private = host in {'localhost', '127.0.0.1', '::1'} or host.endswith('.local')
        try:
            private = private or not ipaddress.ip_address(host).is_global
        except ValueError:
            pass
        if parsed.scheme not in {'https', 'http'} or not host or parsed.username or parsed.password or private:
            errors.append(key + ': source URL must be public HTTP(S) without credentials')
        if source['checked_on'] > today or (source['published_on'] and source['published_on'] > source['checked_on']):
            errors.append(key + ': invalid source date order')
    seen = set()
    for rule in data['restrictions']['rules']:
        key = rule['rule_id']
        if key in seen:
            errors.append('duplicate restriction rule ID ' + key)
        seen.add(key)
        errors.extend(audit_errors(rule, key))
        if rule['action'] != ACTIONS[rule['rule_type']]:
            errors.append(key + ': rule type and action disagree')
        if rule['review_due_on'] < rule['audit']['created_on']:
            errors.append(key + ': review due date precedes creation')
        scope = rule['scope']
        if scope['kind'] == 'families':
            for reference in scope['family_ids']:
                if reference not in families:
                    errors.append(key + ': unknown family ' + reference)
        elif scope['kind'] == 'exercises':
            for reference in scope['exercise_ids']:
                if reference not in exercises:
                    errors.append(key + ': unknown exercise ' + reference)
        elif scope['kind'] == 'attributes':
            found, _ = condition_errors(scope['condition'], exercise_fields, inputs, True)
            errors.extend(key + ': ' + message for message in found)
        found, refs = condition_errors(rule['trigger'], exercise_fields, inputs)
        errors.extend(key + ': ' + message for message in found)
        if set(rule['required_inputs']) != refs:
            errors.append(key + ': required_inputs must exactly list referenced input IDs')
        for reference in rule['source_ids']:
            source = sources.get(reference)
            if source is None:
                errors.append(key + ': unknown source ' + reference)
            elif rule['status'] == 'approved' and source['status'] != 'approved':
                errors.append(key + ': approved rule requires approved sources')
    return errors

def truth(node, exercise, inputs):
    """Kleene-style boolean evaluation; None is unknown, including under NOT."""
    op = node['op']
    if op in {'all', 'any', 'not'}:
        children = [node['condition']] if op == 'not' else node['conditions']
        results = [truth(child, exercise, inputs) for child in children]
        values = [value for value, _ in results]
        if op == 'not':
            return (None if values[0] is None else not values[0]), results[0][1]
        decisive = False if op == 'all' else True
        if any(value is decisive for value in values):
            return decisive, set()
        if any(value is None for value in values):
            return None, set().union(*(missing for _, missing in results))
        return not decisive, set()
    namespace, key = node['field']['namespace'], node['field']['key']
    fields = exercise if namespace == 'exercise' else inputs
    if key not in fields:
        return None, {namespace + '.' + key}
    actual, expected = fields[key], node['value']
    if op in NUMERIC and not numeric(actual):
        return None, {namespace + '.' + key}
    if op == 'eq': result = actual == expected
    elif op == 'ne': result = actual != expected
    elif op == 'in': result = actual in expected
    elif op == 'not_in': result = actual not in expected
    elif op == 'lt': result = actual < expected
    elif op == 'lte': result = actual <= expected
    elif op == 'gt': result = actual > expected
    elif op == 'gte': result = actual >= expected
    else: raise ValueError('Unsupported rule operator')
    return result, set()

def evaluate_validated(data, exercise, context, today=None):
    """Internal evaluator. Public evaluate_catalog validates the full snapshot first."""
    today = today or date.today().isoformat()
    definitions = {item['input_id']: item for item in data['restriction_dictionary']['inputs']}
    reasons, valid_inputs = [], {}
    if not isinstance(context, dict):
        reasons.append({'code': 'invalid_context'})
        context = {}
    for key, value in context.items():
        if key not in definitions:
            reasons.append({'code': 'unrecognized_input', 'field': key})
        elif not fits(definitions[key]['value_schema'], value) or (isinstance(value, float) and not math.isfinite(value)):
            reasons.append({'code': 'invalid_input', 'field': key})
        else:
            valid_inputs[key] = value
    excluded = exercise['status'] == 'retired'
    if exercise['status'] != 'approved':
        reasons.append({'code': 'exercise_not_approved'})
    if exercise['restriction_review']['status'] != 'reviewed':
        reasons.append({'code': 'restrictions_not_assessed'})
    matches, missing, evaluated = [], set(), []
    for rule in data['restrictions']['rules']:
        if rule['status'] == 'retired':
            continue
        scope = rule['scope']
        kind = scope['kind']
        scope_missing = set()
        if kind == 'all_exercises': applies = True
        elif kind == 'families': applies = exercise['family_id'] in scope['family_ids']
        elif kind == 'exercises': applies = exercise['exercise_id'] in scope['exercise_ids']
        elif kind == 'attributes': applies, scope_missing = truth(scope['condition'], exercise, valid_inputs)
        else: raise ValueError('Unsupported scope')
        if applies is False:
            continue
        triggered, trigger_missing = truth(rule['trigger'], exercise, valid_inputs)
        if triggered is False:
            continue
        evaluated.append({'rule_id': rule['rule_id'], 'revision': rule['audit']['revision']})
        if applies is None or triggered is None:
            reasons.append({'code': 'unknown_condition', 'rule_id': rule['rule_id']})
            missing.update(scope_missing | trigger_missing)
            continue
        if rule['status'] != 'approved' or rule['review_due_on'] < today:
            reasons.append({'code': 'rule_needs_review', 'rule_id': rule['rule_id']})
            continue
        matches.append({key: rule[key] for key in ('rule_id', 'rule_type', 'action', 'rationale', 'source_ids')})
        if rule['action'] == 'exclude':
            excluded = True
        elif rule['action'] == 'require_review':
            reasons.append({'code': 'review_trigger', 'rule_id': rule['rule_id']})
    outcome = ('excluded' if excluded else 'review_required' if reasons else
               'precaution' if matches else 'no_matching_rule')
    return {'exercise_id': exercise['exercise_id'], 'catalog_version': data['variants']['schema_version'],
            'outcome': outcome, 'matching_rules': matches, 'review_reasons': reasons,
            'missing_fields': sorted(missing), 'rule_versions': evaluated}
