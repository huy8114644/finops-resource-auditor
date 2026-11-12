# Finding triage and realized savings

Reports identify review candidates. They do not authorize deletion and are not billing statements.

1. Confirm account, region, inventory timestamp and permission errors. Treat incomplete scans as incomplete.
2. Find the workload owner through tags and deployment records. Keep unknown ownership candidates on hold.
3. Check retention policy, backups, legal holds and restore requirements. Snapshot age alone does not establish safe deletion.
4. Review estimated cost assumptions against AWS pricing in that region. Snapshot storage is incremental; provisioned size is an upper bound.
5. Obtain an explicit change ticket and owner approval. Perform any cleanup with a separate controlled operational process.
6. Re-run read-only discovery and compare Cost Explorer billing after the reporting delay. Record verified savings separately from estimates.

ECR tag age can hide shared image digests; an idle load balancer can serve failover or seasonal traffic. Check dependencies and a representative observation window before action.
