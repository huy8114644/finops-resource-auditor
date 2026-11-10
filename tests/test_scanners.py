from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import boto3
import pytest
from botocore.stub import Stubber

from finops_auditor.scanners import AWSFinOpsScanner, build_summary

NOW = datetime(2026, 1, 15, tzinfo=UTC)
OLD = NOW - timedelta(days=100)
REGION = "us-east-1"
ARN = "arn:aws:elasticloadbalancing:us-east-1:111122223333:loadbalancer/app/demo/123"
TG = "arn:aws:elasticloadbalancing:us-east-1:111122223333:targetgroup/demo/123"
REPO = "arn:aws:ecr:us-east-1:111122223333:repository/demo"


def scanner(service, **kwargs):
    client = boto3.client(service)
    session = Mock()
    session.client.return_value = client
    return AWSFinOpsScanner([REGION], session=session, now=NOW, **kwargs), Stubber(client)


def test_volume_pagination_age_state_tags():
    scan, stub = scanner("ec2")
    volume = {
        "VolumeId": "vol-old",
        "State": "available",
        "VolumeType": "gp3",
        "Size": 100,
        "CreateTime": OLD,
        "Attachments": [],
    }
    params = {"Filters": [{"Name": "status", "Values": ["available"]}]}
    stub.add_response("describe_volumes", {"Volumes": [volume], "NextToken": "next"}, params)
    stub.add_response(
        "describe_volumes",
        {
            "Volumes": [
                dict(
                    volume, VolumeId="vol-ignored", Tags=[{"Key": "finops:ignore", "Value": "TRUE"}]
                ),
                dict(volume, VolumeId="vol-young", CreateTime=NOW),
                dict(volume, VolumeId="vol-attached", Attachments=[{"State": "attached"}]),
            ]
        },
        dict(params, NextToken="next"),
    )
    with stub:
        findings = scan.scan_unattached_ebs(REGION)
        stub.assert_no_pending_responses()
    assert len(findings) == 1
    assert findings[0].estimated_monthly_savings_usd == 8
    assert "Detach age is unknown" in findings[0].reason


def test_snapshot_is_unpriced_and_paginated():
    scan, stub = scanner("ec2")
    snap = {"SnapshotId": "snap-old", "StartTime": OLD, "State": "completed", "VolumeSize": 900}
    stub.add_response(
        "describe_snapshots", {"Snapshots": [], "NextToken": "next"}, {"OwnerIds": ["self"]}
    )
    stub.add_response(
        "describe_snapshots",
        {
            "Snapshots": [
                snap,
                dict(snap, State="pending"),
                dict(snap, StartTime=NOW),
                dict(snap, Tags=[{"Key": "finops:ignore", "Value": "true"}]),
            ]
        },
        {"OwnerIds": ["self"], "NextToken": "next"},
    )
    with stub:
        findings = scan.scan_stale_snapshots(REGION)
        stub.assert_no_pending_responses()
    summary = build_summary(findings, [REGION], NOW)
    assert summary.unpriced_findings == 1
    assert summary.total_estimated_monthly_savings_usd == 0


def test_load_balancer_and_target_group_pagination():
    scan, stub = scanner("elbv2")
    lb = {
        "LoadBalancerArn": ARN,
        "LoadBalancerName": "demo",
        "CreatedTime": OLD,
        "Type": "application",
    }
    stub.add_response("describe_load_balancers", {"LoadBalancers": [], "NextMarker": "next"}, {})
    stub.add_response("describe_load_balancers", {"LoadBalancers": [lb]}, {"Marker": "next"})
    stub.add_response("describe_tags", {"TagDescriptions": []}, {"ResourceArns": [ARN]})
    stub.add_response(
        "describe_target_groups",
        {"TargetGroups": [], "NextMarker": "page2"},
        {"LoadBalancerArn": ARN},
    )
    stub.add_response(
        "describe_target_groups",
        {"TargetGroups": [{"TargetGroupArn": TG}]},
        {"LoadBalancerArn": ARN, "Marker": "page2"},
    )
    stub.add_response(
        "describe_target_health", {"TargetHealthDescriptions": []}, {"TargetGroupArn": TG}
    )
    with stub:
        findings = scan.scan_idle_load_balancers(REGION)
        stub.assert_no_pending_responses()
    assert len(findings) == 1
    assert findings[0].estimated_monthly_savings_usd == 16.43


def test_registered_unhealthy_targets_are_not_declared_idle():
    scan, stub = scanner("elbv2")
    stub.add_response(
        "describe_load_balancers",
        {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": ARN,
                    "LoadBalancerName": "demo",
                    "CreatedTime": OLD,
                    "Type": "network",
                }
            ]
        },
        {},
    )
    stub.add_response("describe_tags", {"TagDescriptions": []}, {"ResourceArns": [ARN]})
    stub.add_response(
        "describe_target_groups",
        {"TargetGroups": [{"TargetGroupArn": TG}]},
        {"LoadBalancerArn": ARN},
    )
    stub.add_response(
        "describe_target_health",
        {
            "TargetHealthDescriptions": [
                {"Target": {"Id": "i-test"}, "TargetHealth": {"State": "unhealthy"}}
            ]
        },
        {"TargetGroupArn": TG},
    )
    with stub:
        assert scan.scan_idle_load_balancers(REGION) == []


@pytest.mark.parametrize("tagged", [False, True])
def test_ecr_real_sizes_age_and_pagination(tagged):
    scan, stub = scanner("ecr", include_tagged_ecr=tagged)
    image = {"imageDigest": "sha256:abc", "imagePushedAt": OLD, "imageSizeInBytes": 2**30}
    stub.add_response("describe_repositories", {"repositories": [], "nextToken": "next"}, {})
    stub.add_response(
        "describe_repositories",
        {"repositories": [{"repositoryName": "demo", "repositoryArn": REPO}]},
        {"nextToken": "next"},
    )
    stub.add_response("list_tags_for_resource", {"tags": []}, {"resourceArn": REPO})
    params = {"repositoryName": "demo", "filter": {"tagStatus": "ANY" if tagged else "UNTAGGED"}}
    stub.add_response("describe_images", {"imageDetails": [], "nextToken": "more"}, params)
    stub.add_response(
        "describe_images",
        {
            "imageDetails": [
                image,
                dict(image, imagePushedAt=NOW),
                dict(image, imageTags=["latest"]),
                dict(image, imageDigest="sha256:tagged", imageTags=["v1"]),
            ]
        },
        dict(params, nextToken="more"),
    )
    with stub:
        findings = scan.scan_old_ecr_images(REGION)
        stub.assert_no_pending_responses()
    assert len(findings) == (2 if tagged else 1)
    assert findings[0].estimated_monthly_savings_usd == 0.10


def test_api_failure_is_not_silently_a_clean_report():
    scan, stub = scanner("ec2")
    stub.add_client_error("describe_volumes", service_error_code="AccessDenied")
    with stub, pytest.raises(Exception, match="AccessDenied"):
        scan.run_all()


def test_all_scanners_regions_and_deduplication():
    scan = AWSFinOpsScanner([REGION, REGION, "eu-west-1"], session=Mock(), now=NOW)
    for method in (
        "scan_unattached_ebs",
        "scan_stale_snapshots",
        "scan_idle_load_balancers",
        "scan_old_ecr_images",
    ):
        setattr(scan, method, Mock(return_value=[]))
    assert scan.run_all().regions == [REGION, "eu-west-1"]
    assert scan.scan_old_ecr_images.call_count == 2


def test_invalid_thresholds_and_empty_regions():
    with pytest.raises(ValueError):
        AWSFinOpsScanner([], session=Mock())
    with pytest.raises(ValueError):
        AWSFinOpsScanner([REGION], volume_days=-1, session=Mock())


def test_inclusive_volume_threshold_and_unknown_cost():
    scan, stub = scanner("ec2", volume_days=14)
    volume = {
        "VolumeId": "vol-boundary",
        "State": "available",
        "VolumeType": "gp3",
        "Size": 1,
        "CreateTime": NOW - timedelta(days=14),
        "Attachments": [],
    }
    stub.add_response(
        "describe_volumes",
        {
            "Volumes": [
                volume,
                dict(volume, VolumeId="vol-under", CreateTime=NOW - timedelta(days=13)),
            ]
        },
        {"Filters": [{"Name": "status", "Values": ["available"]}]},
    )
    with stub:
        findings = scan.scan_unattached_ebs(REGION)
    assert len(findings) == 1
    assert findings[0].age_days == 14
    from finops_auditor.pricing import ebs_estimate, lb_estimate

    assert ebs_estimate("unknown", 100) is None
    assert lb_estimate("gateway") is None
