# FinOps Resource Auditor

Read-only Python CLI for AWS cost review: unattached EBS volumes, old snapshots,
load balancers with no registered targets, and old ECR images. It produces local
JSON reports and optional Slack/Telegram summaries. There are no deletion APIs.

## Quick start (offline)

Python 3.11+ is required. No AWS account or credentials are needed for the demo.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
finops-audit --demo
finops-audit --demo --format json --output report.json
finops-audit --fixture fixtures/demo.json
```

The bundled fixture contains four synthetic findings: an illustrative **$32.68/month
priced subtotal**, plus one unpriced snapshot. The demo timestamp and resources are
fixed; demo mode does not apply live inventory thresholds.

## Live read-only inventory

Use an AWS profile or a short-lived role. Credentials follow boto3's standard chain;
never store keys in this repository. Supply regions explicitly; there is no account
or region auto-discovery. Scans run sequentially and paginate every inventory list.

```bash
AWS_PROFILE=finops-readonly finops-audit --live \
  --regions us-east-1,ap-southeast-1 \
  --volume-days 14 --snapshot-days 90 --image-days 30 --lb-days 14 \
  --output report.json
```

Thresholds are inclusive whole days and nonnegative. EBS age is creation age, **not
detach age**. Snapshot age alone says nothing about retention obligations or AMI
and backup references. Load balancers are candidates only when they have zero
registered targets at scan time; this is not a traffic history analysis. Unhealthy
registered targets do not qualify. Classic load balancers are not scanned.

ECR defaults to untagged images. `--include-tagged-ecr` also reviews old tagged images;
`--protected-tags latest,prod,production,stable` excludes exact, case-sensitive tag
names. Push time is not last use. Verify ECS/EKS, rollback and multi-architecture
manifest references manually. `finops:ignore=true` excludes volumes, snapshots,
load balancers and ECR repositories. It is a review convention, not access control.

API/credential/region failures stop the command with a nonzero exit; no partial
report is labeled successful. Successful scans exit 0, including scans with findings.
The output file is replaced only after the scan completes. Treat reports as sensitive
inventory; do not publish production reports as public CI artifacts.

## Cost assumptions

Rates are illustrative static US East examples, not current regional price quotes.
See [cost methodology](docs/cost-methodology.md) before using the report in a budget.
The subtotal excludes unpriced candidates; ECR figures can double-count shared layers.
No finding is approval to remove a resource. This tool never changes AWS resources.

## Notifications (optional)

Notifications send a short aggregate summary only, and run only with `--notify`.
Set `FINOPS_SLACK_WEBHOOK` for Slack; set `FINOPS_TELEGRAM_TOKEN` and
`FINOPS_TELEGRAM_CHAT_ID` for Telegram. Keep these in a secret store/environment,
not shell history or source control. The generated local report remains available
if delivery fails, but the command exits nonzero. Demo notifications are real
outbound messages if explicitly requested.

```bash
finops-audit --demo --notify slack
finops-audit --demo --notify telegram
```

## Development and automation

```bash
ruff check .
ruff format --check .
mypy src
pytest
python -m build
```

Tests use botocore Stubber with dummy credentials and disabled instance metadata;
no cloud account is contacted. Coverage must remain at least 85%. CI runs lint,
format, strict type checking, tests, package builds and an offline demo on Python
3.11 and 3.12. A daily scheduled run repeats these checks and uploads synthetic
reports. It uses no cloud secrets and never schedules live scans automatically.
See [read-only IAM](docs/read-only-policy.json) for required actions. The example
policy uses wildcard resources for inventory API compatibility; narrow account,
region and repository access according to your organization's policies.

MIT licensed. Contributions should include a clear use case and offline validation.
