# Cost methodology and review workflow

| Candidate | Illustrative USD rate | What the estimate means |
| --- | --- | --- |
| EBS gp3/gp2 | 0.08 / 0.10 per provisioned GiB-month | Storage only; excludes performance charges |
| EBS io1/io2 | 0.125 per provisioned GiB-month | Excludes IOPS charges |
| EBS standard/sc1/st1 | 0.05 / 0.015 / 0.045 per GiB-month | Storage only |
| ALB/NLB | 0.0225/hour × 730 = 16.43/month rounded | Base cost only; excludes capacity/traffic |
| ECR | 0.10 per GiB-month using reported image bytes | Potential overestimate from shared layers |
| Snapshot | Unpriced (`null`) | VolumeSize is not incremental billable storage |

These are representative baseline examples, not a dated/current AWS quote. They
apply unchanged across regions, so compare with your own regional invoice or the
AWS Pricing Calculator before planning savings. Unknown EBS/LB types are unpriced.
Prices exclude discounts, Savings Plans, taxes, transfer and other attached services.
The total sums known rounded estimates for triage; it is not an achievable-savings
forecast. Untagged and old images may still be used; billing may persist through
shared layers or snapshot dependencies. Snapshot archive/tier details are not analyzed.

Review workflow:

1. Confirm owner, production dependencies, recovery objectives and retention rules.
2. Check deployment/rollback image references, AMIs, AWS Backup, and legal holds.
3. Validate observed traffic, listeners, fixed responses and DNS for load balancers.
4. Reconcile cost with current regional billing data and account discounts.
5. Handle approved changes in a separate change-management workflow, then compare bills.

The auditor intentionally implements no cleanup command. ECR lifecycle policies,
snapshot lifecycle management and infrastructure-as-code changes belong in a
separately reviewed workflow. Service API reads may incur AWS charges or throttling;
this repository's tests and scheduled checks only use offline fixtures/stubs.
