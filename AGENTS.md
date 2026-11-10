# Repository Guidelines

## Structure and boundaries

`src/finops_auditor/` contains the read-only scanner, typed result models, CLI,
pricing assumptions, notifications and bundled demo fixture. `tests/` exercises
AWS request contracts with botocore Stubber. `fixtures/demo.json` mirrors the
package fixture for local examples. `docs/` explains IAM and cost assumptions.

Keep this repository strictly read-only for AWS: do not add deletion, tagging,
policy mutation, or cleanup execution commands. Notifications must remain explicit
opt-in actions. Do not run live AWS scans or send messages during development.

## Development checks

Create `.venv` with `python3 -m venv .venv` and install `pip install -e '.[dev]'`.
Before submitting, run `ruff check .`, `ruff format --check .`, `mypy src`,
`pytest`, and `python -m build`. Verify `finops-audit --demo --format json` and
keep the installed wheel's fixture available. CI repeats checks on Python 3.11
and 3.12, including daily offline runs. Do not introduce cloud credentials to CI.

## Style and tests

Use four spaces, `snake_case` functions, `PascalCase` classes, and annotations.
Ruff enforces imports, formatting and a 100-column limit. Mypy checks production
code in strict mode; `Any` is reserved for documented dynamic boto3 boundaries
and heterogeneous AWS metadata. Keep policy decisions separate from cost claims.

Name tests `test_*.py`. Add Stubber cases for changed AWS calls, pagination,
threshold boundaries and exclusions. Tests use dummy credentials and disabled
instance metadata. Preserve the 85% coverage gate; test behavior rather than
implementation details. Update both fixtures if their schema changes.

## Contributions and reporting

Use conventional commit subjects such as `feat: add candidate filter` or
`fix: paginate image details`. PR descriptions should explain behavior changes,
validation, IAM additions and limitations. Do not claim current prices or proven
idle time without supporting data. Never commit reports with real inventory,
AWS credentials, webhooks, bot tokens, virtual environments or generated builds.
