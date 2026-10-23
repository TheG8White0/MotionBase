"""Evaluate a validated MotionBase catalog against ephemeral, private context facts."""
import argparse
import json
from pathlib import Path
import sys
from common import read_json
from validate_model import load_model, validate_model
from safety import evaluate_validated

def evaluate_catalog(data, schema, exercise_id, context):
    errors = validate_model(data, schema)
    if errors:
        raise ValueError('Catalog validation failed: ' + '; '.join(errors))
    record = next((item for item in data['variants']['variants'] if item['exercise_id'] == exercise_id), None)
    if record is None:
        raise ValueError('Unknown exercise ID')
    return evaluate_validated(data, record, context)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--exercise-id', required=True)
    parser.add_argument('--context', type=Path, help='Private JSON object with only declared input IDs; never copied to the catalog')
    args = parser.parse_args(argv)
    try:
        data, schema = load_model(args.root)
        result = evaluate_catalog(data, schema, args.exercise_id, read_json(args.context) if args.context else {})
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
