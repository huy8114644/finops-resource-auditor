"""CLI for read-only FinOps candidate discovery."""

import argparse
import json
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from .models import AuditSummary, WasteFinding
from .notify import notify
from .scanners import AWSFinOpsScanner, build_summary


def load_fixture(path: Path | None) -> AuditSummary:
    raw = path.read_text() if path else files("finops_auditor").joinpath("demo.json").read_text()
    data = json.loads(raw)
    findings = [WasteFinding(**item) for item in data["findings"]]
    return build_summary(findings, data["regions"], datetime.fromisoformat(data["scanned_at"]))


def render_text(summary: AuditSummary) -> str:
    lines = [
        f"FinOps Audit ({summary.scanned_at})",
        f"Regions: {', '.join(summary.regions)} | Findings: {summary.total_findings} | "
        f"Priced: ${summary.total_estimated_monthly_savings_usd:.2f}/mo | "
        f"Unpriced: {summary.unpriced_findings}",
        summary.disclaimer,
    ]
    for f in summary.findings:
        price = (
            "unpriced"
            if f.estimated_monthly_savings_usd is None
            else (f"${f.estimated_monthly_savings_usd:.2f}/mo")
        )
        lines.append(f"- [{f.region}] {f.resource_type} {f.resource_id} ({price}): {f.reason}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--regions", default="us-east-1")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="Use bundled offline fixture")
    mode.add_argument("--fixture", type=Path, help="Load an offline fixture JSON file")
    mode.add_argument(
        "--live", action="store_true", help="Read AWS inventory using local credentials"
    )
    p.add_argument(
        "--notify", choices=("slack", "telegram"), help="Send a brief summary explicitly"
    )
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--output", type=Path, help="Write JSON report to path")
    p.add_argument("--snapshot-days", type=int, default=90)
    p.add_argument("--volume-days", type=int, default=14)
    p.add_argument("--image-days", type=int, default=30)
    p.add_argument("--lb-days", type=int, default=14)
    p.add_argument("--include-tagged-ecr", action="store_true")
    p.add_argument("--protected-tags", default="latest,prod,production,stable")
    args = p.parse_args(argv)
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    tags = tuple(t.strip() for t in args.protected_tags.split(",") if t.strip())
    try:
        summary = (
            load_fixture(args.fixture)
            if args.demo or args.fixture
            else AWSFinOpsScanner(
                regions,
                snapshot_days=args.snapshot_days,
                volume_days=args.volume_days,
                image_days=args.image_days,
                lb_days=args.lb_days,
                include_tagged_ecr=args.include_tagged_ecr,
                protected_tags=tags,
            ).run_all()
        )
    except ValueError as err:
        p.error(str(err))
    payload = json.dumps(summary.to_dict(), indent=2)
    if args.output:
        args.output.write_text(payload + "\n")
    print(payload if args.format == "json" else render_text(summary))
    if args.notify:
        notify(
            args.notify,
            f"FinOps audit: {summary.total_findings} review candidates; "
            f"illustrative priced subtotal ${summary.total_estimated_monthly_savings_usd:.2f}/mo; "
            f"{summary.unpriced_findings} unpriced. Review the full local report before acting.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
