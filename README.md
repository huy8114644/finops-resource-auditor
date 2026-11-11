# FinOps Resource Auditor

[![Offline quality checks](https://github.com/huy8114644/finops-resource-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/huy8114644/finops-resource-auditor/actions/workflows/ci.yml)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python)](https://python.org)
[![AWS: Read Only](https://img.shields.io/badge/AWS-Strictly%20Read%20Only-orange.svg?logo=amazon-aws)](docs/read-only-policy.json)
[![Coverage: 95%+](https://img.shields.io/badge/Coverage-95.5%25-success.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Production-grade, **Read-Only AWS FinOps CLI and Automation Engine** that discovers abandoned cloud assets, calculates transparent cost savings estimates, and alerts engineering teams without modifying cloud state.

---

## 🎯 Problem Statement & Core Value

Over 30% of enterprise cloud spend is wasted on abandoned, orphaned resources — unattached EBS volumes left after EC2 termination, aged snapshots without retention policies, idle Application Load Balancers with zero registered targets, and legacy container images.

This tool delivers safe, automated FinOps governance:
1. **Strictly Read-Only:** Zero deletion or mutation APIs; safe to execute in production environments without change advisory boards.
2. **Transparent Cost Methodology:** Plainly documents assumptions (storage rates, base hourly ELB rates) and marks non-attributable assets (EBS snapshot incremental blocks) as `unpriced` rather than guessing.
3. **Multi-Region & Automated Alerts:** Dispatches executive summary reports to Slack incoming webhooks or Telegram bot channels.

---

## 🏛️ FinOps Auditing Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Multi-Region Read-Only Ingestion (Boto3)"]
        A[AWS EC2: DescribeVolumes<br/>Status: Available]
        B[AWS EC2: DescribeSnapshots<br/>Owner: Self, Age > Threshold]
        C[AWS ELBv2: DescribeLoadBalancers<br/>Zero Healthy / Registered Targets]
        D[AWS ECR: DescribeImages<br/>Untagged or Stale Push Date]
    end

    subgraph Engine ["2. FinOps Analysis & Policy Filter"]
        A & B & C & D --> E{Tag Evaluator}
        E -->|finops:ignore=true| F[Skip / Exclude Resource]
        E -->|Protected Tags<br/>latest, prod, stable| F
        E -->|Qualifies as Candidate| G[Finding Generator<br/>WasteFinding Schema]
    end

    subgraph Pricing ["3. Transparent Pricing Engine"]
        G --> H[EBS Storage Rate: Provisioned GiB x $0.08]
        G --> I[ELB Base Rate: $0.0225/hr x 730 hrs]
        G --> J[ECR Layer Rate: Image Bytes x $0.10/GiB]
        G --> K[Snapshot Volume: Intentionally Unpriced]
    end

    subgraph Reports ["4. Actionable Reporting & Notification"]
        H & I & J & K --> L[AuditSummary Report]
        L --> M[Terminal Plain Text Table]
        L --> N[Structured JSON Report File]
        L --> O[Slack / Telegram Webhook Alerts]
    end

    classDef dark fill:#0d1117,stroke:#238636,stroke-width:1.5px,color:#c9d1d9;
    class Ingestion,Engine,Pricing,Reports dark;
```

---

## 🔒 Resource Detection & Cost Methodology

| Target Resource | Qualification Rule | Pricing Model | Caveat & Review Guidance |
|---|---|---|---|
| **Unattached EBS** | `State == 'available'` & age >= `volume_days` | Provisioned GiB × $0.08/mo (gp3) | Detach timestamp is unrecorded by AWS; verify snapshot history |
| **Aged Snapshots** | `State == 'completed'` & age >= `snapshot_days` | **Unpriced** (`null`) | Provisioned size is not billed incremental delta; check AMI dependencies |
| **Idle Load Balancers** | Zero registered targets across all target groups | Base hourly rate ($0.0225/hr × 730 hrs) | Excludes capacity units (LCU); verify DNS cutover before decommissioning |
| **Old ECR Images** | Untagged or age >= `image_days` (unprotected) | Uncompressed size × $0.10/GiB | Shared layers can overstate savings; verify rollback tags |

---

## ⚙️ Environment Variables & Configuration

The auditor is configured via environment variables and CLI arguments:

| Variable | Type | Default | Description |
|---|---|---|---|
| `AWS_PROFILE` | String | `null` | Named AWS CLI profile granting read-only credentials |
| `AWS_DEFAULT_REGION` | String | `us-east-1` | Default fallback AWS region |
| `FINOPS_SLACK_WEBHOOK` | String | `null` | Slack incoming webhook URL for automated summary delivery |
| `FINOPS_TELEGRAM_TOKEN` | String | `null` | Telegram Bot token for incident alerts |
| `FINOPS_TELEGRAM_CHAT_ID` | String | `null` | Telegram channel or group chat ID |

---

## 🚀 Local Developer Quickstart

Standardized operational tasks are automated via the included `Makefile`:

```bash
# 1. View all available Makefile commands
make help

# 2. Setup virtual environment and development dependencies
make setup

# 3. Run Ruff linter and code formatting check
make lint

# 4. Run Mypy static type verification (strict mode)
make typecheck

# 5. Execute Pytest test suite with code coverage
make test

# 6. Execute offline FinOps discovery demo (no AWS account required)
make audit-demo
```

---

## ☸️ Live AWS Multi-Region Scanning

```bash
# Run against live AWS account with custom thresholds
finops-audit --live \
  --regions us-east-1,us-west-2,ap-southeast-1 \
  --volume-days 14 \
  --snapshot-days 90 \
  --lb-days 14 \
  --output live-report.json

# Send summary alert to Slack
finops-audit --demo --notify slack
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
