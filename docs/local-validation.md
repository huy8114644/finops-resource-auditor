# Local validation evidence

Run on 2026-11-12 (Asia/Ho_Chi_Minh), on the uncommitted `docs/portfolio-standards` changes. This is local checkout evidence, not a remote CI result or a live savings report.

Tools: Python 3.13.5, Ruff 0.17.4, Gitleaks Docker image v8.24.3. CI separately declares Python 3.11/3.12; those interpreter versions were not rerun locally.

| Check | Result |
| --- | --- |
| Default `make` | Help only |
| `make lint` | Ruff lint and format checks passed |
| `make typecheck` | Strict mypy passed for 6 source files |
| `make test` | 21 passed, 95.54% local coverage (85% gate) |
| `make plan` | JSON from bundled synthetic fixture; 4 findings, 1 unpriced |
| `make build` | Source archive and wheel built |
| Fresh isolated wheel install | `--no-deps` install and offline JSON demo passed outside checkout |
| `make scan` | Passed after replacing a synthetic invalid-token test literal |
| `git diff --check` | Passed |

The first Gitleaks run correctly failed on the synthetic `test_telegram_invalid_token` value. Its replacement still contains the forbidden slash, preserving the rejection behavior without resembling an API key. No scanner errors or findings are swallowed. The scan covers current directory content rather than Git history.

Setup was not repeated because the checkout already had a development environment. No live AWS inventory was read and no notifications were sent. The wheel check verifies the packaged fixture without installing boto3 in that isolated environment; boto3 is needed for live mode. Real AWS account permissions, regional API behavior, current pricing and delivery destinations remain unverified here. No host or cloud apply was performed.
