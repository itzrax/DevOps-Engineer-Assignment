#!/usr/bin/env python3
"""
NimbusKart Cost Janitor
Scans AWS for orphaned/wasted resources and generates a cost report.
"""

import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import boto3
from botocore.config import Config

from constants import REQUIRED_TAGS, DEFAULT_STOPPED_DAYS, LOCALSTACK_ENDPOINT, DEFAULT_REGION, PRICING


def get_client(service: str, use_localstack: bool = True):
    """Create a boto3 client pointed at LocalStack or real AWS."""
    if use_localstack:
        return boto3.client(
            service,
            region_name=DEFAULT_REGION,
            endpoint_url=LOCALSTACK_ENDPOINT,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    return boto3.client(service, region_name=DEFAULT_REGION)

def is_protected(tags: list) -> bool:
    """Return True if resource has Protected=true tag."""
    if not tags:
        return False
    return any(
        t["Key"] == "Protected" and t["Value"].lower() == "true"
        for t in tags
    )

def get_tag_value(tags: list, key: str) -> str:
    """Get value of a specific tag."""
    if not tags:
        return ""
    for t in tags:
        if t["Key"] == key:
            return t["Value"]
    return ""

def check_missing_tags(tags: list) -> list:
    """Return list of required tags that are missing."""
    if not tags:
        return REQUIRED_TAGS.copy()
    existing = {t["Key"] for t in tags}
    return [t for t in REQUIRED_TAGS if t not in existing]

def find_orphan_ebs_volumes(ec2, dry_run: bool) -> list:
    """Find EBS volumes not attached to any instance."""
    findings = []
    response = ec2.describe_volumes(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )

    for vol in response["Volumes"]:
        tags = vol.get("Tags", [])
        if is_protected(tags):
            continue

        size_gb = vol["Size"]
        monthly_cost = size_gb * PRICING["ebs_gp3_per_gb"]

        finding = {
            "resource_type": "ebs_volume",
            "resource_id": vol["VolumeId"],
            "region": DEFAULT_REGION,
            "reason": "EBS volume not attached to any instance",
            "estimated_monthly_cost_usd": monthly_cost,
            "tags": tags,
            "action": "delete" if not dry_run else "would_delete",
        }
        findings.append(finding)

        if not dry_run:
            ec2.delete_volume(VolumeId=vol["VolumeId"])
            print(f"  [DELETED] EBS volume {vol['VolumeId']}")
        else:
            print(f"  [DRY-RUN] Would delete EBS volume {vol['VolumeId']} (${monthly_cost:.2f}/mo)")

    return findings

def find_stopped_instances(ec2, dry_run: bool, stopped_days: int) -> list:
    """Find EC2 instances stopped for more than stopped_days days."""
    findings = []
    response = ec2.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=stopped_days)

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            tags = instance.get("Tags", [])
            if is_protected(tags):
                continue

            # LocalStack may not have StateTransitionReason, so we handle that
            state_reason = instance.get("StateTransitionReason", "")
            stopped_since = None

            try:
                if "(" in state_reason and ")" in state_reason:
                    date_str = state_reason.split("(")[1].split(")")[0]
                    stopped_since = datetime.strptime(
                        date_str, "%Y-%m-%d %H:%M:%S %Z"
                    ).replace(tzinfo=timezone.utc)
            except Exception:
                pass

            if stopped_since and stopped_since > cutoff:
                continue

            finding = {
                "resource_type": "ec2_instance",
                "resource_id": instance["InstanceId"],
                "region": DEFAULT_REGION,
                "reason": f"EC2 instance stopped for more than {stopped_days} days",
                "estimated_monthly_cost_usd": PRICING["ec2_t3_micro"],
                "tags": tags,
                "action": "delete" if not dry_run else "would_delete",
            }
            findings.append(finding)

            if not dry_run:
                ec2.terminate_instances(InstanceIds=[instance["InstanceId"]])
                print(f"  [DELETED] EC2 instance {instance['InstanceId']}")
            else:
                print(f"  [DRY-RUN] Would terminate EC2 instance {instance['InstanceId']}")

    return findings

def find_unassociated_eips(ec2, dry_run: bool) -> list:
    """Find Elastic IPs not associated with any instance."""
    findings = []
    response = ec2.describe_addresses()

    for eip in response["Addresses"]:
        tags = eip.get("Tags", [])
        if is_protected(tags):
            continue

        if eip.get("AssociationId"):
            continue

        finding = {
            "resource_type": "elastic_ip",
            "resource_id": eip.get("AllocationId", eip.get("PublicIp")),
            "region": DEFAULT_REGION,
            "reason": "Elastic IP not associated with any instance",
            "estimated_monthly_cost_usd": PRICING["elastic_ip"],
            "tags": tags,
            "action": "delete" if not dry_run else "would_delete",
        }
        findings.append(finding)

        if not dry_run:
            ec2.release_address(AllocationId=eip["AllocationId"])
            print(f"  [DELETED] Elastic IP {eip.get('PublicIp')}")
        else:
            print(f"  [DRY-RUN] Would release Elastic IP {eip.get('PublicIp')}")

    return findings

def find_missing_tags(ec2, dry_run: bool) -> list:
    """Find resources missing required tags."""
    findings = []

    # Check EC2 instances
    response = ec2.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            tags = instance.get("Tags", [])
            missing = check_missing_tags(tags)
            if missing:
                finding = {
                    "resource_type": "ec2_instance",
                    "resource_id": instance["InstanceId"],
                    "region": DEFAULT_REGION,
                    "reason": f"Missing required tags: {', '.join(missing)}",
                    "estimated_monthly_cost_usd": 0.0,
                    "tags": tags,
                    "action": "flag",
                }
                findings.append(finding)
                print(f"  [TAG] EC2 {instance['InstanceId']} missing tags: {missing}")

    # Check EBS volumes
    vol_response = ec2.describe_volumes()
    for vol in vol_response["Volumes"]:
        tags = vol.get("Tags", [])
        missing = check_missing_tags(tags)
        if missing:
            finding = {
                "resource_type": "ebs_volume",
                "resource_id": vol["VolumeId"],
                "region": DEFAULT_REGION,
                "reason": f"Missing required tags: {', '.join(missing)}",
                "estimated_monthly_cost_usd": 0.0,
                "tags": tags,
                "action": "flag",
            }            
            findings.append(finding)
            print(f"  [TAG] EBS {vol['VolumeId']} missing tags: {missing}")

    return findings

def generate_markdown(findings: list, total_cost: float) -> str:
    """Generate a markdown summary report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# NimbusKart Cost Janitor Report",
        f"**Generated:** {now}",
        f"**Total findings:** {len(findings)}",
        f"**Estimated monthly waste:** ${total_cost:.2f}",
        "",
        "## Findings",
        "",
    ]

    if not findings:
        lines.append("No orphaned resources found.")
    else:
        for f in findings:
            lines.append(f"### {f['resource_type']} — {f['resource_id']}")
            lines.append(f"- **Reason:** {f['reason']}")
            lines.append(f"- **Estimated cost:** ${f['estimated_monthly_cost_usd']:.2f}/mo")
            lines.append(f"- **Action:** {f['action']}")
            lines.append("")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="NimbusKart Cost Janitor")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview findings without deleting anything (default: True)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        default=False,
        help="Actually delete orphaned resources",
    )
    parser.add_argument(
        "--stopped-days",
        type=int,
        default=DEFAULT_STOPPED_DAYS,
        help=f"Days a stopped instance is considered orphaned (default: {DEFAULT_STOPPED_DAYS})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory to write report files (default: current directory)",
    )
    parser.add_argument(
        "--use-localstack",
        action="store_true",
        default=True,
        help="Point to LocalStack instead of real AWS",
    )
    args = parser.parse_args()

    dry_run = not args.delete
    ec2 = get_client("ec2", use_localstack=args.use_localstack)

    print("\n🔍 NimbusKart Cost Janitor")
    print(f"   Mode: {'DRY RUN' if dry_run else 'DELETE'}")
    print(f"   Stopped instance threshold: {args.stopped_days} days\n")

    all_findings = []

    print("Checking orphan EBS volumes...")
    all_findings += find_orphan_ebs_volumes(ec2, dry_run)

    print("Checking stopped EC2 instances...")
    all_findings += find_stopped_instances(ec2, dry_run, args.stopped_days)

    print("Checking unassociated Elastic IPs...")
    all_findings += find_unassociated_eips(ec2, dry_run)

    print("Checking missing tags...")
    all_findings += find_missing_tags(ec2, dry_run)

    total_cost = sum(f["estimated_monthly_cost_usd"] for f in all_findings)

    # Build report.json
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "total_findings": len(all_findings),
        "estimated_monthly_waste_usd": round(total_cost, 2),
        "findings": all_findings,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "report.json"
    md_path = output_dir / "report.md"

    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    with open(md_path, "w") as f:
        f.write(generate_markdown(all_findings, total_cost))

    print(f"\n✅ Done! {len(all_findings)} findings, ${total_cost:.2f}/mo estimated waste")
    print(f"   Report: {json_path}")
    print(f"   Summary: {md_path}")

if __name__ == "__main__":
    main()   