---
title: "Cost Management: Cost Explorer, CUR & Data Transfer"
---

# Cost Management: Cost Explorer, CUR & Data Transfer

[AWS Budgets](storage-and-observability.md#aws-budgets-cost-alerts-tracking)
already covers setting alerts before spend gets out of hand, and
[EC2 Purchasing Options](ec2-instance-types-and-purchasing-options.md#purchasing-options-trading-flexibility-for-discount)
covers Savings Plans and Spot. This page covers the tools for
understanding spend *after* the fact, and the cost most people forget
to account for at all: moving data around.

## Cost Explorer

Visual, interactive analysis of **historical** spend — filter and group
by service, linked account, tag, region, or instance type; spot a cost
spike and drill into exactly what caused it.

- Built-in **forecasting**, based on historical usage patterns.
- Includes **Savings Plans / Reserved Instance recommendations**,
  calculated from actual historical usage — a concrete, data-driven
  answer to "how much would committing actually save us," rather than
  guessing.
- Good for **"what happened, and why"** — an interactive, exploratory
  tool, not a raw export.

## Cost and Usage Reports (CUR)

The most **detailed, granular** billing data AWS produces — every line
item, delivered as CSV/Parquet files to an S3 bucket on a schedule,
built for feeding into your own analysis (Athena, QuickSight, a
third-party FinOps tool) rather than reading directly.

!!! success "The exam signal"

    "Need the most granular possible billing data, to build custom
    cost-allocation reports or feed into our own BI tool" → CUR. "Just
    need to explore spend trends interactively, no custom tooling" →
    Cost Explorer. CUR is the raw data; Cost Explorer is AWS's own
    pre-built way to look at it.

## Data Transfer Costs: The One Everyone Forgets

Compute and storage get all the attention; data transfer is the line
item that surprises people, because the pricing isn't symmetric.

| Transfer | Cost |
|---|---|
| Data **in** to AWS, from the internet | Free |
| Data **out** to the internet | Charged, and it's the single biggest data-transfer cost in most bills |
| Between **AZs**, same region | Charged in both directions |
| Between **regions** | Charged, more than cross-AZ |
| Within the **same AZ** | Free |
| Through a **VPC endpoint** (S3, DynamoDB) instead of a NAT Gateway | Free (gateway endpoint) or a smaller endpoint-processing charge (interface endpoint) instead of the NAT Gateway's per-GB charge |

!!! success "The exam signal"

    "Reduce data transfer costs for traffic between an application and
    S3" →
    [a VPC Gateway Endpoint](vpc-connectivity-and-hybrid-networking.md#vpc-endpoints-reaching-aws-services-without-the-internet),
    removing the NAT Gateway's per-GB charge for that traffic entirely.
    "Reduce cost for a globally distributed user base pulling the same
    content repeatedly" →
    [CloudFront](cloudfront-cdn.md), since edge-cached responses don't
    re-incur origin data-transfer-out charges on every request. Placing
    resources that talk to each other constantly in the **same AZ**
    (where that's compatible with the availability requirements) avoids
    cross-AZ charges that are easy to miss until the bill arrives.
