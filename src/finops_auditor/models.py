"""Serializable audit results."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class WasteFinding:
    resource_type: str
    resource_id: str
    region: str
    reason: str
    estimated_monthly_savings_usd: float | None
    estimate_basis: str
    age_days: int
    # AWS responses and resource metadata have heterogeneous JSON values.
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditSummary:
    scanned_at: str
    regions: list[str]
    total_findings: int
    total_estimated_monthly_savings_usd: float
    unpriced_findings: int
    findings: list[WasteFinding]
    disclaimer: str = (
        "Review candidates only. Estimates use static example USD rates, not live regional quotes; "
        "they are not guaranteed savings. Snapshot storage is unpriced. No resources are changed."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
