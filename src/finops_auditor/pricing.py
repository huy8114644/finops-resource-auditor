"""Illustrative US East baseline rates, not a current AWS price feed.

730 hours/month. EBS provisioned IOPS/throughput, discounts, taxes, LB capacity and
transfer are excluded. ECR image sizes may double-count shared layers.
"""

EBS_GIB_MONTH = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "standard": 0.05,
    "sc1": 0.015,
    "st1": 0.045,
}


def ebs_estimate(volume_type: str, size_gib: int) -> float | None:
    rate = EBS_GIB_MONTH.get(volume_type)
    return None if rate is None else round(size_gib * rate, 2)


def lb_estimate(lb_type: str) -> float | None:
    return 16.43 if lb_type in {"application", "network"} else None


def ecr_estimate(size_bytes: int) -> float:
    return round(size_bytes / 2**30 * 0.10, 4)
