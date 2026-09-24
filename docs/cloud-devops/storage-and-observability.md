---
title: "Storage, Secrets & Observability on AWS"
---

# Storage, Secrets & Observability on AWS

Hands-on notes from a personal AWS lab, covering the "keep the lights on"
half of running a real service on AWS: S3 for object storage (lifecycle,
versioning, replication), Secrets Manager and Parameter Store for
configuration, CloudWatch and X-Ray for observability, and AWS Budgets so
a forgotten resource doesn't quietly burn through the account. Every CLI
command below was run against a real account, not copied from docs.

## S3 Deep Dive

### Lifecycle policies

Lifecycle policies automatically transition objects between storage
classes to optimize cost:

```
Day 0:   Standard        ($0.023/GB)  ← hot data, frequent access
Day 30:  Standard-IA     ($0.0125/GB) ← infrequent access, lower cost
Day 90:  Glacier Instant  ($0.004/GB)  ← archive, millisecond retrieval
Day 365: Delete                        ← remove old data
```

- Set this once on the bucket and S3 moves objects automatically — no
  scripts, no cron job, no manual re-tiering.

### Versioning

- Versioning keeps all versions of every object.
- If a file is accidentally overwritten or deleted, the previous version
  still exists.
- Deleting a versioned object adds a "delete marker" instead of actually
  removing it — the object is hidden but not gone, and can be restored.

!!! note "Requirement"

    - Cross-region replication requires versioning enabled on both the
      source and destination buckets.
    - Only *new* objects replicate automatically — existing objects have
      to be copied manually, e.g. with `aws s3 sync`.

### Cross-region replication

- Replication to a bucket in another region is asynchronous.
- It's used for disaster recovery (RPO) and compliance (keeping data in
  specific regions).
- Combined with lifecycle policies, the replicated bucket can use
  cheaper storage classes than the source.

### CLI: S3 bucket operations

``` bash
# Create a bucket (name must be globally unique)
aws s3 mb s3://fahad-ecommerce-assets-dev

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket fahad-ecommerce-assets-dev \
  --versioning-configuration Status=Enabled

# Upload a file
aws s3 cp ./logo.png s3://fahad-ecommerce-assets-dev/images/logo.png

# Upload an entire folder
aws s3 sync ./static/ s3://fahad-ecommerce-assets-dev/static/

# List objects
aws s3 ls s3://fahad-ecommerce-assets-dev/ --recursive

# Download a file
aws s3 cp s3://fahad-ecommerce-assets-dev/images/logo.png ./downloaded-logo.png

# Set lifecycle policy (Standard → IA after 30 days → Glacier after 90)
aws s3api put-bucket-lifecycle-configuration \
  --bucket fahad-ecommerce-assets-dev \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "archive-old-objects",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 365}
    }]
  }'

# Check bucket size and object count
aws s3 ls s3://fahad-ecommerce-assets-dev/ --recursive --summarize \
  | tail -2

# Block all public access (security best practice)
aws s3api put-public-access-block \
  --bucket fahad-ecommerce-assets-dev \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Delete all objects and the bucket
aws s3 rb s3://fahad-ecommerce-assets-dev --force
```

## Secrets Manager & Parameter Store

| Feature | Secrets Manager | Parameter Store (SSM) |
|---|---|---|
| **Purpose** | Passwords, API keys, DB credentials | Configuration values, feature flags, non-secret config |
| **Auto rotation** | Yes — Lambda rotates credentials on a schedule | No built-in rotation |
| **Cost** | $0.40/secret/month + API calls | Free tier (standard params), $0.05/advanced/month |
| **Hierarchy** | Flat names | Hierarchical paths: `/app/prod/db-host` |
| **Use when** | DB passwords, third-party API keys | App config, feature flags, non-sensitive settings |

``` bash
# Store a database password
aws secretsmanager create-secret \
  --name ecommerce/prod/db-password \
  --secret-string '{"username":"app","password":"s3cureP@ss"}'

# Retrieve it (your app does this at startup)
aws secretsmanager get-secret-value \
  --secret-id ecommerce/prod/db-password \
  --query SecretString --output text

# Update (rotate) a secret
aws secretsmanager update-secret \
  --secret-id ecommerce/prod/db-password \
  --secret-string '{"username":"app","password":"n3wP@ssw0rd"}'

# List all secrets
aws secretsmanager list-secrets \
  --query "SecretList[].{Name:Name,LastChanged:LastChangedDate}" \
  --output table

# Delete a secret (has a 7-day recovery window by default)
aws secretsmanager delete-secret \
  --secret-id ecommerce/prod/db-password

# --- Parameter Store (SSM) ---

# Store a config value (not secret — use StringType)
aws ssm put-parameter \
  --name "/ecommerce/dev/app-port" \
  --value "8080" \
  --type String

# Store a secret value (encrypted)
aws ssm put-parameter \
  --name "/ecommerce/dev/api-key" \
  --value "sk-abc123" \
  --type SecureString

# Retrieve a parameter
aws ssm get-parameter \
  --name "/ecommerce/dev/app-port" \
  --query "Parameter.Value" --output text

# Retrieve with decryption (for SecureString)
aws ssm get-parameter \
  --name "/ecommerce/dev/api-key" \
  --with-decryption \
  --query "Parameter.Value" --output text

# List all parameters under a path
aws ssm get-parameters-by-path \
  --path "/ecommerce/dev/" \
  --query "Parameters[].{Name:Name,Value:Value}" \
  --output table
```

!!! danger "Never"

    - Never hardcode secrets in application code, Dockerfiles,
      environment files committed to Git, or Terraform state.
    - Always read secrets from Secrets Manager or Parameter Store at
      runtime instead.

Aurora RDS credentials (see [AWS Services Quick Reference](aws-services.md))
are a natural fit for this — pairing a managed Postgres/MySQL instance
with Secrets Manager for rotation is a common pattern worth knowing
alongside Aurora itself.

## CloudWatch — Metrics, Alarms & Logs

### Metrics

- Every AWS service publishes metrics to CloudWatch automatically — EC2
  CPU utilization, RDS connections, ALB request count, S3 bucket size,
  and more.
- Custom metrics can also be published directly from an app.

### Alarms

Alarms trigger actions when a metric crosses a threshold:

``` bash
# Alert when CPU exceeds 80% for 5 minutes
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu-web \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:ap-south-1:111122223333:alerts
```

An alarm can trigger any of:

- SNS notifications (email/SMS)
- Auto Scaling actions
- Lambda functions
- Systems Manager actions

### CLI: CloudWatch metrics and alarms

``` bash
# Create an SNS topic for alerts (you need this for alarm actions)
aws sns create-topic --name fahad-alerts \
  --query "TopicArn" --output text

# Subscribe your email to the topic
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-south-1:111122223333:fahad-alerts \
  --protocol email \
  --notification-endpoint fahadmdkamal@gmail.com
# Check your email and click "Confirm subscription"

# Create alarm: high CPU on an instance
aws cloudwatch put-metric-alarm \
  --alarm-name fahad-high-cpu-web \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:ap-south-1:111122223333:fahad-alerts \
  --dimensions Name=InstanceId,Value=i-xxxxx

# Create alarm: high 5xx errors on ALB
aws cloudwatch put-metric-alarm \
  --alarm-name fahad-alb-5xx-errors \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:ap-south-1:111122223333:fahad-alerts

# List all alarms
aws cloudwatch describe-alarms \
  --query "MetricAlarms[].{Name:AlarmName,State:StateValue,Metric:MetricName}" \
  --output table

# Get CPU metrics for an instance (last 1 hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxxxx \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --output table
```

### Dashboards

- Build a visual dashboard per environment.
- Include request rate, error rate (5xx), latency p50/p95/p99, CPU
  utilization, active DB connections, and disk usage.
- This is the first thing to look at during an incident.

### CLI: Logs

CloudWatch Logs centralizes logs from all services. Structure:

```
Log group:   /ecs/ecommerce-prod     ← one per service per environment
Log stream:  instance-i-0aee8c/app    ← one per source (instance, container)
Log events:  individual log lines      ← timestamped, searchable
```

``` bash
# Create a log group
aws logs create-log-group \
  --log-group-name /ec2/fahad-web-dev

# List log groups
aws logs describe-log-groups \
  --query "logGroups[].{Name:logGroupName,Size:storedBytes}" \
  --output table

# Tail logs in real-time (requires aws-cli v2)
aws logs tail /ec2/fahad-web-dev --follow

# Search logs for errors (last 1 hour)
aws logs filter-log-events \
  --log-group-name /ec2/fahad-web-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --query "events[].{Time:timestamp,Message:message}" \
  --output table

# Delete a log group (cleanup)
aws logs delete-log-group \
  --log-group-name /ec2/fahad-web-dev
```

**Log Insights** queries across all log streams with SQL-like syntax (in
the Console → CloudWatch → Logs → Insights):

``` sql
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 50
```

## X-Ray Distributed Tracing

X-Ray traces a request as it flows through the entire system — from the
ALB, through the app, to the database, to any external APIs — and shows
exactly where time is spent.

```
Trace: GET /api/orders
├── ALB: 2ms
├── Django app: 145ms
│   ├── Auth middleware: 3ms
│   ├── DB query (orders): 89ms  ← bottleneck!
│   ├── DB query (users): 12ms
│   └── Serialize response: 41ms
└── Total: 147ms
```

- Without X-Ray, debugging "the API is slow" means guessing.
- With X-Ray, the trace shows exactly which call is the bottleneck — here
  an 89ms database query — so the next step is `EXPLAIN`, not a guess.

!!! success "Django context"

    - The `aws-xray-sdk` Python package patches Django, `requests`,
      `boto3`, and `psycopg2` automatically.
    - Add it to middleware and every request is traced — no
      per-function instrumentation needed.

## AWS Budgets — Cost Alerts & Tracking

- AWS Budgets sets spending limits and sends email alerts when spend
  approaches or exceeds them.
- This matters most on a personal learning account — one forgotten NAT
  Gateway or ALB left running can eat through the account's credits
  overnight with nobody watching.

### Method 1: Inline (single command, no files)

``` bash
aws budgets create-budget \
  --account-id 111122223333 \
  --budget '{
    "BudgetName": "ramp-plan-fahad",
    "BudgetLimit": {"Amount": "80", "Unit": "USD"},
    "TimeUnit": "QUARTERLY",
    "BudgetType": "COST",
    "TimePeriod": {
      "Start": "2026-09-01T00:00:00Z",
      "End": "2026-12-31T23:59:59Z"
    }
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 50,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "EMAIL",
        "Address": "fahadmdkamal@gmail.com"
      }]
    },
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "EMAIL",
        "Address": "fahadmdkamal@gmail.com"
      }]
    }
  ]' \
  --profile fahad
```

### Method 2: File-based (separate JSON files — cleaner for version control)

Create two files, then reference them:

**budget.json:**

``` json
{
  "BudgetName": "ramp-plan-fahad",
  "BudgetLimit": {
    "Amount": "80",
    "Unit": "USD"
  },
  "TimeUnit": "QUARTERLY",
  "BudgetType": "COST",
  "CostTypes": {
    "IncludeTax": true,
    "IncludeSubscription": true,
    "UseBlended": false,
    "IncludeRefund": false,
    "IncludeCredit": false,
    "IncludeUpfront": true,
    "IncludeRecurring": true,
    "IncludeOtherSubscription": true,
    "IncludeSupport": true,
    "IncludeDiscount": true,
    "UseAmortized": false
  },
  "TimePeriod": {
    "Start": "2026-09-01T00:00:00Z",
    "End": "2026-12-31T23:59:59Z"
  }
}
```

!!! danger "Date format"

    - Dates must be ISO 8601, e.g. `2026-09-01T00:00:00Z` — with `T`
      between date and time, and `Z` for UTC.
    - Using underscores (`2026-09-01_00:00`) or omitting `Z` will fail.

**notifications.json:**

``` json
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 50,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [{
      "SubscriptionType": "EMAIL",
      "Address": "fahadmdkamal@gmail.com"
    }]
  },
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [{
      "SubscriptionType": "EMAIL",
      "Address": "fahadmdkamal@gmail.com"
    }]
  }
]
```

!!! danger "Gotcha"

    - The notifications file must be a bare JSON **array** `[...]`, not
      an object `{"NotificationWithSubscribers": [...]}`.
    - The CLI flag already names the parameter — the file provides just
      the value.

**The command:**

``` bash
# cd into the directory containing the JSON files first
cd ~/Desktop/devops-syllabus

aws budgets create-budget \
  --account-id 111122223333 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json \
  --profile fahad
```

!!! note "file:// paths"

    - `file://budget.json` is relative to the current directory.
    - Use `file:///full/path/budget.json` (triple slash) for absolute
      paths, or `cd` into the directory first.

### Method 3: AWS Console

- Go to **AWS Console → Billing → Budgets → Create budget**.
- The guided wizard generates the same thing as the CLI, but through a
  visual form.
- Good for one-off budgets; the CLI is better for reproducibility.

### All possible field values — reference

**Budget object fields:**

| Field | Possible values | Description |
|---|---|---|
| `BudgetName` | Any string (unique per account) | Name for the budget. Used in describe/delete commands. |
| `BudgetLimit.Amount` | Any number as a **string** — e.g. `"80"`, `"100.50"` | Must be a string, not a number. `"80"` not `80`. |
| `BudgetLimit.Unit` | `USD` \| `GB` \| `HOURS` | `USD` for cost budgets. `GB` or `HOURS` for usage budgets. |
| `BudgetType` | `COST` \| `USAGE` \| `RI_UTILIZATION` \| `RI_COVERAGE` \| `SAVINGS_PLANS_UTILIZATION` \| `SAVINGS_PLANS_COVERAGE` | `COST` tracks dollars spent. `USAGE` tracks resource consumption (hours, GB). The RI/SP types track reserved instance and savings plan efficiency. |
| `TimeUnit` | `DAILY` \| `MONTHLY` \| `QUARTERLY` \| `ANNUALLY` | How the budget resets. `MONTHLY` = $80/month. `QUARTERLY` = $80/quarter. `DAILY` = $80/day (unusual). |

**TimePeriod:**

| Field | Format | Example |
|---|---|---|
| `Start` | ISO 8601 timestamp | `2026-09-01T00:00:00Z` |
| `End` | ISO 8601 timestamp | `2026-12-31T23:59:59Z` |

!!! note "Tip"

    If omitted, `TimePeriod` defaults to starting immediately with no
    end date — the budget recurs forever at the `TimeUnit` interval,
    which is fine for ongoing monitoring.

**CostTypes (all booleans — what to include in the cost calculation):**

| Field | Default | When to change |
|---|---|---|
| `IncludeTax` | `true` | Set `false` to track pre-tax spend only |
| `IncludeSubscription` | `true` | Includes marketplace subscriptions |
| `IncludeCredit` | `true` | Set `false` to see raw spend before credits are applied — **recommended for learning** so you see what you'd actually owe |
| `IncludeRefund` | `true` | Include refunds in the calculation |
| `IncludeSupport` | `true` | Include AWS Support plan charges |
| `IncludeDiscount` | `true` | Include volume and bundled discounts |
| `UseBlended` | `false` | Set `true` for blended rate (averaged across linked accounts in an Organization) |
| `UseAmortized` | `false` | Set `true` to spread upfront RI/SP payments across their term |
| `IncludeUpfront` | `true` | Include one-time upfront fees |
| `IncludeRecurring` | `true` | Include recurring monthly fees |
| `IncludeOtherSubscription` | `true` | Include other subscription costs |

**CostFilters (optional — narrow budget to specific services):**

``` json
// Track ALL services (recommended — don't add this field)
// No CostFilters = everything is tracked

// Track only EC2
"CostFilters": {
  "Service": ["Amazon Elastic Compute Cloud - Compute"]
}

// Track only RDS and EC2
"CostFilters": {
  "Service": [
    "Amazon Elastic Compute Cloud - Compute",
    "Amazon Relational Database Service"
  ]
}

// Track only a specific tag
"CostFilters": {
  "TagKeyValue": ["user:Project$ecommerce-platform"]
}
```

!!! danger "Recommendation"

    - Don't filter by service for a learning budget — it'll miss things
      like NAT Gateway ($32/month) and ALB ($16/month) that aren't EC2.
    - Track everything instead.

**Notification fields:**

| Field | Possible values | Description |
|---|---|---|
| `NotificationType` | `ACTUAL` \| `FORECASTED` | `ACTUAL` = alert when you've already spent X. `FORECASTED` = alert when AWS predicts you'll exceed X by end of period. |
| `ComparisonOperator` | `GREATER_THAN` \| `LESS_THAN` \| `EQUAL_TO` | Usually `GREATER_THAN`. `LESS_THAN` is useful for RI utilization ("alert if utilization drops below 80%"). |
| `Threshold` | 0–100 (when `PERCENTAGE`) or absolute number | The value to compare against. 50 = 50% or $50 depending on ThresholdType. |
| `ThresholdType` | `PERCENTAGE` \| `ABSOLUTE_VALUE` | `PERCENTAGE` = % of BudgetLimit. `ABSOLUTE_VALUE` = exact dollar amount. |

**Subscriber fields:**

| Field | Possible values | Description |
|---|---|---|
| `SubscriptionType` | `EMAIL` \| `SNS` | `EMAIL` sends directly to the address. `SNS` publishes to an SNS topic (can trigger Lambda, Slack, PagerDuty). |
| `Address` | Email address or SNS topic ARN | Where the alert goes. |

### Manage existing budgets

``` bash
# List all budgets
aws budgets describe-budgets \
  --account-id 111122223333 \
  --query "Budgets[].{Name:BudgetName,Limit:BudgetLimit.Amount,Spent:CalculatedSpend.ActualSpend.Amount,Type:BudgetType,TimeUnit:TimeUnit}" \
  --output table \
  --profile fahad

# Update a budget (change the limit to $100)
aws budgets update-budget \
  --account-id 111122223333 \
  --new-budget '{
    "BudgetName": "ramp-plan-fahad",
    "BudgetLimit": {"Amount": "100", "Unit": "USD"},
    "TimeUnit": "QUARTERLY",
    "BudgetType": "COST",
    "TimePeriod": {
      "Start": "2026-09-01T00:00:00Z",
      "End": "2026-12-31T23:59:59Z"
    }
  }' \
  --profile fahad

# Delete a budget
aws budgets delete-budget \
  --account-id 111122223333 \
  --budget-name "ramp-plan-fahad" \
  --profile fahad

# Check current spend vs budget
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-09-30 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --profile fahad

# Spend breakdown by service (find what's costing the most)
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-09-30 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --profile fahad
```

### Common budget patterns

| Pattern | Settings | Use case |
|---|---|---|
| **Zero-spend trip-wire** | Limit: $1, TimeUnit: MONTHLY, Threshold: 80% | Catch any unexpected spend immediately. Alert at $0.80. |
| **Learning budget** | Limit: $80, TimeUnit: QUARTERLY, Thresholds: 50% + 80% | A full quarter's practice budget with an early and late warning. |
| **Monthly guard rail** | Limit: $50, TimeUnit: MONTHLY, Threshold: 90% | Per-month cap for ongoing projects. |
| **Forecast alert** | NotificationType: FORECASTED, Threshold: 100% | Alert before you exceed — AWS predicts the trajectory and warns early. |
| **Per-service budget** | CostFilter on SERVICE, Limit: $30 | Track one expensive service (e.g. RDS only). |
| **Per-project budget** | CostFilter on TagKeyValue, Limit: $100 | Track spend by project tag — requires tagged resources. |
