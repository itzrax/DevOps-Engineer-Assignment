# Design Note — NimbusKart Cost Janitor

## 1. Multi-cloud support (AWS → GCP / Azure)

Right now the janitor is built mainly around `boto3`, so it is tightly coupled with AWS.
If NimbusKart adds GCP or Azure later, rewriting the whole logic would become messy. To avoid that, the core detection logic can be separated from the cloud-specific APIs using a provider-based structure.

```python
class CloudProvider:
    def list_unattached_volumes(self): ...
    def list_stopped_instances(self): ...
    def list_unassociated_ips(self): ...
    def list_untagged_resources(self): ...
```

Each cloud provider would implement its own version of these functions:

* `AWSProvider` → boto3
* `GCPProvider` → google-cloud-compute
* `AzureProvider` → azure-mgmt libraries

The main janitor workflow would stay the same.
Only the provider object changes depending on which cloud is selected.

Example:

```bash
python janitor.py --provider aws
python janitor.py --provider gcp
python janitor.py --provider azure
```

This keeps the project modular and makes future expansion easier without touching the main cleanup logic.

---

## 2. IAM permissions required

The janitor needs two levels of permissions:

* **Read-only permissions** for scanning resources in dry-run mode
* **Delete permissions** when running with `--delete`

Example IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "JanitorReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeInstances",
        "ec2:DescribeAddresses",
        "ec2:DescribeTags",
        "s3:ListAllMyBuckets",
        "s3:GetBucketTagging"
      ],
      "Resource": "*"
    },
    {
      "Sid": "JanitorDelete",
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume",
        "ec2:TerminateInstances",
        "ec2:ReleaseAddress"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:ResourceTag/Protected": "true"
        }
      }
    }
  ]
}
```

The important part here is the `Protected=true` condition.
Even if the script accidentally tries to delete a protected resource, AWS itself blocks the action. So IAM acts like a second safety layer.

---

## 3. Two failure scenarios that could cause outages

### Failure mode 1 — Wrongly deleting active resources

Sometimes a volume may look unused for a short time during maintenance operations like snapshots, resizing, or migrations. If the janitor scans during that period, it could mistakenly treat the volume as orphaned and delete it.

**Mitigation:**
Instead of deleting immediately, add a grace period check.

Example:

* only delete if unattached for more than 24 hours
* avoid acting on temporary states

---

### Failure mode 2 — Terraform state becoming inconsistent

If someone manually deletes infrastructure outside Terraform, the state file may no longer match reality. Later, running `terraform apply` could recreate resources unexpectedly or create configuration drift.

**Mitigation:**

* use remote Terraform state
* enable DynamoDB state locking
* prevent concurrent or unmanaged infrastructure changes

This keeps the Terraform state authoritative and reduces accidental recreation issues.

---

## 4. FinOps metrics to monitor

| Metric                           | Purpose                                               |
| -------------------------------- | ----------------------------------------------------- |
| `janitor.orphans_found`          | Shows how much unused infrastructure exists over time |
| `janitor.estimated_waste_usd`    | Estimates monthly cloud cost waste                    |
| `janitor.scan_duration_seconds`  | Detects scaling/performance issues in large accounts  |
| `janitor.resources_deleted`      | Tracks cleanup activity for auditing                  |
| `janitor.missing_tag_violations` | Measures tagging compliance improvement               |

These metrics could be pushed to services like CloudWatch or Datadog for dashboards and monitoring.

---

## 5. Features intentionally left out

### Unit tests

The `tests/` folder is currently empty.
If more time was available, tools like `moto` would be used to mock AWS services and test cleanup logic safely.

---

### RDS / AMI cleanup

RDS snapshots and unused AMIs are common cost issues, but scanning them requires additional IAM permissions and more complex logic. They were skipped to keep the project manageable within the assignment timeline.

---

### Notifications

Slack or email alerts would be useful in a real production FinOps workflow, especially before deletion actions. They were not included because the assignment focused mainly on detection and cleanup logic.

---

### Remote Terraform backend

Remote state storage using S3 + DynamoDB was intentionally not configured because the assignment was designed to run fully locally with LocalStack and no real AWS account.

---

### S3 lifecycle policies

Lifecycle rules were kept commented out due to compatibility issues in LocalStack Community Edition. In a real AWS deployment, they would normally be enabled.

