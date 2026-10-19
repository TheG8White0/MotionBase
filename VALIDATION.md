# Automated validation

## Run locally
Create a virtual environment, activate it, and install requirements-validation.txt.
```text
python -B -m unittest discover -s tests -v
python -B scripts/validate.py
python -B scripts/validate.py --base-ref origin/main
```
The baseline command requires Git history and the actual target branch/ref. The first two commands work before Git initialization. They do not modify the exercise database.

## What fails validation
- Malformed JSON, repeated JSON keys, non-finite numbers, invalid dates or unknown schema attributes.
- Incorrect ID format, duplicate exercise/context/source IDs, or category/schema disagreement.
- Missing required fields for an approved record or missing review identity/date.
- Broken source references, nonexistent/self exercise links, or approved links to unapproved variants.
- Nonpositive active dose/sets, reversed or incomplete ranges, values in inactive dose fields, or inconsistent effort fields.
- Inconsistent load metric, unit and load basis; invalid source URLs or missing external-reference provenance.
- Future or unordered audit dates and approval predating the latest update.
- Obvious prohibited client/contact fields, possible email/telephone values, local filesystem paths or unexpected repository files.
- With --base-ref: deletion of accepted IDs, changed records without increased revision, or changed creation dates.

Repository scope allows the database, schema, taxonomy, project documentation, Python scripts/tests, and GitHub configuration. Only local .git/.venv/cache directories are skipped. New file types need a reviewed validator change.

## GitHub Actions
.github/workflows/validate.yml runs tests and validation on pull requests, main-branch pushes, merge groups and manual dispatch. Pull requests compare against the target commit. The workflow uses read-only repository permissions and no model credentials. Its job/check is named validate.

After creating the repository:
- Protect main with required pull requests and the validate check; dismiss stale approvals and require discussion resolution.
- Add the owner's actual GitHub account to CODEOWNERS, then require code-owner approval.
- Keep merge access with the owner. Require a current agent report as a manual merge gate until a real agent integration exists.
- GitHub does not let PR authors approve their own PRs; owner-authored PRs need another eligible reviewer when approval is required.

Repository: https://github.com/TheG8White0/physiodata. The settings above are the required setup; verify their live state in GitHub. Agent review remains a manual merge gate until an agent service is connected.

## Limits
Checks validate structure and selected consistency rules. They do not verify all private information, reference truth, permissions to reuse content, diagnosis, exercise suitability, or human/agent approval authenticity. Review free text, sources, changed tooling and the latest diff personally. No live source fetching or medical inference is performed.

References:
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://github.com/actions/checkout
- https://github.com/actions/setup-python
