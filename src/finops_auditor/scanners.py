"""Paginated inventory scanners. AWS write APIs are intentionally absent."""

from datetime import UTC, datetime
from typing import Any

from .models import AuditSummary, WasteFinding
from .pricing import ebs_estimate, ecr_estimate, lb_estimate


def age_days(value: datetime, now: datetime) -> int:
    return max(0, (now - value.astimezone(UTC)).days)


def ignored(tags: list[dict[str, str]]) -> bool:
    return any(
        t.get("Key") == "finops:ignore" and t.get("Value", "").lower() == "true" for t in tags
    )


class AWSFinOpsScanner:
    def __init__(
        self,
        regions: list[str],
        *,
        snapshot_days: int = 90,
        volume_days: int = 14,
        image_days: int = 30,
        lb_days: int = 14,
        include_tagged_ecr: bool = False,
        protected_tags: tuple[str, ...] = ("latest", "prod", "production", "stable"),
        # boto3 clients are dynamically generated and intentionally use Any at the SDK boundary.
        session: Any = None,
        now: datetime | None = None,
    ) -> None:
        if not regions or any(n < 0 for n in (snapshot_days, volume_days, image_days, lb_days)):
            raise ValueError("regions required and thresholds must be nonnegative")
        self.regions = list(dict.fromkeys(regions))
        self.snapshot_days = snapshot_days
        self.volume_days = volume_days
        self.image_days = image_days
        self.lb_days = lb_days
        self.include_tagged_ecr = include_tagged_ecr
        self.protected_tags = protected_tags
        if session is None:
            import boto3

            session = boto3.Session()
        self.session = session
        self.now = now or datetime.now(UTC)

    def scan_unattached_ebs(self, region: str) -> list[WasteFinding]:
        ec2 = self.session.client("ec2", region_name=region)
        findings = []
        pages = ec2.get_paginator("describe_volumes").paginate(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )
        for page in pages:
            for volume in page.get("Volumes", []):
                age = age_days(volume["CreateTime"], self.now)
                if (
                    volume.get("State") != "available"
                    or volume.get("Attachments")
                    or age < self.volume_days
                    or ignored(volume.get("Tags", []))
                ):
                    continue
                kind, size = volume["VolumeType"], volume["Size"]
                findings.append(
                    WasteFinding(
                        "ebs_unattached",
                        volume["VolumeId"],
                        region,
                        f"Currently unattached; created {age} days ago. Detach age is unknown.",
                        ebs_estimate(kind, size),
                        "Provisioned GiB × static storage-only rate",
                        age,
                        {"volume_type": kind, "size_gib": size},
                    )
                )
        return findings

    def scan_stale_snapshots(self, region: str) -> list[WasteFinding]:
        ec2 = self.session.client("ec2", region_name=region)
        findings = []
        for page in ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"]):
            for snapshot in page.get("Snapshots", []):
                age = age_days(snapshot["StartTime"], self.now)
                if (
                    age < self.snapshot_days
                    or snapshot.get("State") != "completed"
                    or ignored(snapshot.get("Tags", []))
                ):
                    continue
                findings.append(
                    WasteFinding(
                        "snapshot_old",
                        snapshot["SnapshotId"],
                        region,
                        f"Created {age} days ago; verify retention, AMI and backup dependencies.",
                        None,
                        "Unknown: provisioned volume size is not incremental billed storage",
                        age,
                        {
                            "source_volume_size_gib": snapshot.get("VolumeSize"),
                            "source_volume_id": snapshot.get("VolumeId"),
                        },
                    )
                )
        return findings

    def scan_idle_load_balancers(self, region: str) -> list[WasteFinding]:
        elb = self.session.client("elbv2", region_name=region)
        findings = []
        for page in elb.get_paginator("describe_load_balancers").paginate():
            for lb in page.get("LoadBalancers", []):
                age = age_days(lb["CreatedTime"], self.now)
                if age < self.lb_days:
                    continue
                arn = lb["LoadBalancerArn"]
                tag_sets = elb.describe_tags(ResourceArns=[arn]).get("TagDescriptions", [])
                if any(ignored(t.get("Tags", [])) for t in tag_sets):
                    continue
                count = 0
                groups = elb.get_paginator("describe_target_groups").paginate(LoadBalancerArn=arn)
                for group_page in groups:
                    for group in group_page.get("TargetGroups", []):
                        count += len(
                            elb.describe_target_health(TargetGroupArn=group["TargetGroupArn"]).get(
                                "TargetHealthDescriptions", []
                            )
                        )
                if count == 0:
                    findings.append(
                        WasteFinding(
                            "elbv2_no_targets",
                            arn,
                            region,
                            "No registered targets now; verify traffic, listeners "
                            "and fixed responses. "
                            "This is not a historical idle-traffic check.",
                            lb_estimate(lb["Type"]),
                            "Base hourly rate $0.0225 × 730; excludes capacity",
                            age,
                            {"name": lb["LoadBalancerName"], "type": lb["Type"]},
                        )
                    )
        return findings

    def scan_old_ecr_images(self, region: str) -> list[WasteFinding]:
        ecr = self.session.client("ecr", region_name=region)
        findings = []
        for page in ecr.get_paginator("describe_repositories").paginate():
            for repo in page.get("repositories", []):
                name = repo["repositoryName"]
                if ignored(
                    ecr.list_tags_for_resource(resourceArn=repo["repositoryArn"]).get("tags", [])
                ):
                    continue
                status = "ANY" if self.include_tagged_ecr else "UNTAGGED"
                pages = ecr.get_paginator("describe_images").paginate(
                    repositoryName=name, filter={"tagStatus": status}
                )
                for image_page in pages:
                    for image in image_page.get("imageDetails", []):
                        tags = image.get("imageTags", [])
                        age = age_days(image["imagePushedAt"], self.now)
                        if (
                            age < self.image_days
                            or set(tags) & set(self.protected_tags)
                            or (tags and not self.include_tagged_ecr)
                        ):
                            continue
                        size = image["imageSizeInBytes"]
                        findings.append(
                            WasteFinding(
                                "ecr_old_image",
                                f"{name}@{image['imageDigest']}",
                                region,
                                f"Pushed {age} days ago; last use and deployment "
                                "references are unknown.",
                                ecr_estimate(size),
                                "Reported bytes / 2^30 × $0.10; shared layers "
                                "can overstate savings; not additive guaranteed savings",
                                age,
                                {"tags": tags, "size_bytes": size, "repository": name},
                            )
                        )
        return findings

    def run_all(self) -> AuditSummary:
        findings = []
        for region in self.regions:
            findings.extend(self.scan_unattached_ebs(region))
            findings.extend(self.scan_stale_snapshots(region))
            findings.extend(self.scan_idle_load_balancers(region))
            findings.extend(self.scan_old_ecr_images(region))
        return build_summary(findings, self.regions, self.now)


def build_summary(
    findings: list[WasteFinding], regions: list[str], now: datetime | None = None
) -> AuditSummary:
    findings = sorted(findings, key=lambda f: (f.region, f.resource_type, f.resource_id))
    return AuditSummary(
        (now or datetime.now(UTC)).isoformat(),
        regions,
        len(findings),
        round(sum(f.estimated_monthly_savings_usd or 0 for f in findings), 2),
        sum(f.estimated_monthly_savings_usd is None for f in findings),
        findings,
    )
