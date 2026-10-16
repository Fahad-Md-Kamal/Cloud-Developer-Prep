---
title: "Auto Scaling Groups & Scaling Policies"
---

# Auto Scaling Groups & Scaling Policies

Continues from
[Compute & Scaling: EC2, AMIs & Launch Templates](compute-and-scaling.md) —
once an instance is launchable from a Golden AMI via a versioned launch
template, an Auto Scaling Group (ASG) is what turns that single instance
recipe into a self-healing, right-sized fleet. Covers ASG capacity
settings, health checks, AZ placement, lifecycle management, and the
target-tracking/step/scheduled scaling policies that drive it.

## Auto Scaling Groups (ASG)

An ASG maintains a fleet of instances — it ensures you always have the
right number running, replaces unhealthy ones, and spreads them across
AZs.

### Three capacity settings

| Setting | What it means | Example |
|---|---|---|
| **Minimum** | Never go below this, even during scale-in | 1 (always at least 1 running) |
| **Desired** | How many to run right now — ASG launches/terminates to match | 1 (free tier safe with nsl-ledgerly running) |
| **Maximum** | Never go above this, even under heavy load | 3 (budget ceiling) |

### How it works with AZs

- If you set desired=4 across 2 AZs, ASG places 2 in each AZ.
- If AZ-a goes down, ASG launches 2 replacements in AZ-b (up to the max).
- This is automatic fault tolerance — you don't write any code for it.

### Health checks

ASG checks if instances are healthy. Two types:

- **EC2 health check:** is the instance running? (default — catches crashes and hardware failures)
- **ELB health check:** is the ALB's health check passing? (catches app-level failures — process running but returning 500s)

- Always use ELB health checks when you have a load balancer.
- An instance can be "running" (EC2 healthy) but serving errors (ELB unhealthy).
- Without ELB health checks, ASG won't replace it.

### Step 1: Create the launch template (prerequisite)

The ASG needs a launch template to know what to launch — see
[Launch Templates](compute-and-scaling.md#launch-templates) on the
EC2/AMI page.

``` bash
# Verify your launch template exists
aws ec2 describe-launch-templates \
  --launch-template-names ecommerce-web \
  --query "LaunchTemplates[0].{ID:LaunchTemplateId,Name:LaunchTemplateName,Version:LatestVersionNumber}" \
  --output table \
  --profile demo

# Our template: lt-0aaa77778888bbbb (ecommerce-web, references Golden AMI v1.1)
```

### Step 2: Create the ASG

``` bash
# Create with desired=1 to stay within free tier
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name demo-web-asg \
  --launch-template LaunchTemplateName=ecommerce-web,Version='$Latest' \
  --min-size 1 \
  --max-size 3 \
  --desired-capacity 1 \
  --vpc-zone-identifier "subnet-0ccc3333cccc33333,subnet-0ddd4444dddd44444" \
  --tags Key=Name,Value=demo-web-asg,PropagateAtLaunch=true \
         Key=Environment,Value=dev,PropagateAtLaunch=true \
         Key=Owner,Value=demo,PropagateAtLaunch=true \
  --profile demo
```

!!! note "vpc-zone-identifier"

    This specifies which subnets the ASG launches instances into. Using both private app subnets (`demo-private-app-a` + `demo-private-app-b`) across two AZs gives automatic fault tolerance — see [AWS Networking & VPC](aws-networking-vpc.md) for how these subnets were built.

!!! danger "Free tier warning"

    Using `desired-capacity 1` (not 2) because `nsl-ledgerly` is already using the free tier t3.micro allowance. Two t3.micro running simultaneously = the second one costs ~$0.01/hr (~$7.50/month).

### Step 3: Verify the ASG launched an instance

``` bash
# Check ASG status (wait ~30 seconds after creation)
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names demo-web-asg \
  --query "AutoScalingGroups[0].{Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:Instances[].{ID:InstanceId,AZ:AvailabilityZone,Health:HealthStatus,State:LifecycleState}}" \
  --output table \
  --profile demo
```

### Troubleshooting: instances array is empty

If the ASG shows `"Instances": []`, either it's still launching (wait 30 seconds) or something failed. Check the scaling activity log:

``` bash
# Shows WHY a launch failed (wrong subnet, SG not in VPC, quota hit, etc.)
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name demo-web-asg \
  --query "Activities[0].{Status:StatusCode,Desc:Description,Cause:Cause}" \
  --profile demo

# If this returns null, the ASG hasn't even attempted yet — just wait longer

# Full ASG dump (use when --query hides the problem)
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names demo-web-asg \
  --profile demo
```

### Lab: testing scale-out and scale-in

This is the powerful part — manually scaling to see the ASG distribute instances across AZs:

``` bash
# Scale up to 2 instances
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name demo-web-asg \
  --desired-capacity 2 \
  --profile demo

# Wait 30 seconds, then check — should see 2 instances in different AZs
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names demo-web-asg \
  --query "AutoScalingGroups[0].Instances[].{ID:InstanceId,AZ:AvailabilityZone,Health:HealthStatus}" \
  --output table \
  --profile demo
```

**What we observed:**

```
After scale-out to desired=2:
+--------------+----------+-----------------------+
|      AZ      | Health   |          ID           |
+--------------+----------+-----------------------+
|  ap-south-1b |  Healthy |  i-0ccc3333dddd4444  |
|  ap-south-1a |  Healthy |  i-0aaa1111bbbb2222  |
+--------------+----------+-----------------------+
→ ASG automatically placed one in each AZ for fault tolerance
```

#### Why it landed one per AZ — the actual mechanism

It comes down to this one line from the `create-auto-scaling-group` command:

``` bash
--vpc-zone-identifier "subnet-0ccc3333cccc33333,subnet-0ddd4444dddd44444"
```

That gave the ASG two subnets in two different AZs:

```
subnet-0ccc3333cccc33333 = demo-private-app-a → ap-south-1a
subnet-0ddd4444dddd44444 = demo-private-app-b → ap-south-1b
```

The ASG automatically distributes instances across whichever subnets it's given, balancing AZs as it goes:

```
desired=2, 2 subnets → 1 in ap-south-1a, 1 in ap-south-1b
desired=4, 2 subnets → 2 in ap-south-1a, 2 in ap-south-1b
```

!!! danger "One subnet = no fault tolerance"

    - If `--vpc-zone-identifier` had listed only `subnet-0ccc3333cccc33333`, every instance would land in `ap-south-1a` alone — if that AZ goes down, everything goes down.
    - There's no separate "spread across AZs" setting to remember.
    - The ASG only ever launches into the subnets you hand it, so AZ coverage is really a side effect of which subnets you listed.

!!! success "The whole trick"

    Give the ASG subnets in multiple AZs, and it handles the distribution automatically. No extra config, no code — just listing two subnet IDs.

``` bash
# Scale back down to 1 (save money!)
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name demo-web-asg \
  --desired-capacity 1 \
  --profile demo

# Wait 30 seconds, check which one was terminated
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names demo-web-asg \
  --query "AutoScalingGroups[0].Instances[].{ID:InstanceId,AZ:AvailabilityZone}" \
  --output table \
  --profile demo
```

**What we observed:**

```
After scale-in to desired=1:
+--------------+-----------------------+
|      AZ      |          ID           |
+--------------+-----------------------+
|  ap-south-1a |  i-0aaa1111bbbb2222  |
+--------------+-----------------------+
→ ASG terminated the ap-south-1b instance automatically
→ Default termination policy: pick the AZ with more instances, terminate the oldest
```

### ASG termination policies

When the ASG needs to remove an instance during scale-in, it follows a policy:

| Policy | How it picks | Use when |
|---|---|---|
| **Default** | Balance AZs first → oldest launch template → closest to next billing hour | Most cases (what we used) |
| **OldestInstance** | Terminate the longest-running instance | Rolling AMI updates — replace old images first |
| **NewestInstance** | Terminate the most recently launched | Testing — keep the stable old instances |
| **OldestLaunchTemplate** | Terminate instances using the oldest template version | After launch template update — phase out old config |

### Manage ASG lifecycle

``` bash
# Check all ASG details
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names demo-web-asg \
  --query "AutoScalingGroups[0].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,HealthCheck:HealthCheckType,Instances:Instances[].{ID:InstanceId,AZ:AvailabilityZone,Health:HealthStatus}}" \
  --profile demo

# Update settings (e.g. change max from 3 to 6)
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name demo-web-asg \
  --max-size 6 \
  --profile demo

# Force replace all instances with new launch template version (rolling update)
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name demo-web-asg \
  --profile demo

# Protect a specific instance from scale-in (e.g. running a long job)
aws autoscaling set-instance-protection \
  --auto-scaling-group-name demo-web-asg \
  --instance-ids i-xxxxx \
  --protected-from-scale-in \
  --profile demo

# Delete ASG entirely (terminates all its instances)
aws autoscaling delete-auto-scaling-group \
  --auto-scaling-group-name demo-web-asg \
  --force-delete \
  --profile demo
```

### End-of-session cleanup

!!! danger "Budget rule"

    - Since `nsl-ledgerly` uses the free tier t3.micro, any ASG instance costs real money.
    - Delete the ASG at the end of each study session.
    - The launch template and Golden AMI stay (free) — recreating the ASG next session is one command.

``` bash
# Delete ASG (terminates its instances automatically)
aws autoscaling delete-auto-scaling-group \
  --auto-scaling-group-name demo-web-asg \
  --force-delete \
  --profile demo

# Verify no extra instances left running
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].{ID:InstanceId,Name:Tags[?Key=='Name']|[0].Value,Type:InstanceType}" \
  --output table \
  --profile demo
# Should show only nsl-ledgerly
```

### Quick recreation next session

``` bash
# One command to bring the ASG back (template + AMI already exist)
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name demo-web-asg \
  --launch-template LaunchTemplateName=ecommerce-web,Version='$Latest' \
  --min-size 1 \
  --max-size 3 \
  --desired-capacity 1 \
  --vpc-zone-identifier "subnet-0ccc3333cccc33333,subnet-0ddd4444dddd44444" \
  --tags Key=Name,Value=demo-web-asg,PropagateAtLaunch=true \
         Key=Owner,Value=demo,PropagateAtLaunch=true \
  --profile demo
```

## Scaling Policies

### Target tracking (simplest, most common)

Set a target metric, ASG adjusts automatically. You don't define thresholds or step sizes — AWS handles the math:

``` bash
# Keep average CPU at 60%
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name demo-web-asg \
  --policy-name cpu-target-60 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 60.0
  }' \
  --profile demo
```

### What AWS auto-creates for you

When you set a target tracking policy, AWS automatically creates **two CloudWatch alarms**:

| Alarm | What it does | Auto-created name |
|---|---|---|
| **AlarmHigh** | CPU > 60% → scale OUT (add instances) | `TargetTracking-demo-web-asg-AlarmHigh-xxxxx` |
| **AlarmLow** | CPU drops well below 60% → scale IN (remove instances) | `TargetTracking-demo-web-asg-AlarmLow-xxxxx` |

You set one target (60% CPU) and AWS created the entire feedback loop —
monitoring, decision logic, and actions — automatically. This is why
target tracking is the recommended starting point. See
[Storage & Observability](storage-and-observability.md) for more on
CloudWatch alarms and metrics generally.

``` bash
# See the auto-created alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "TargetTracking-demo-web-asg" \
  --query "MetricAlarms[].{Name:AlarmName,State:StateValue,Threshold:Threshold}" \
  --output table \
  --profile demo
```

### Lab output — what we got

```
Policy created:
  PolicyARN: arn:aws:autoscaling:ap-south-1:111122223333:scalingPolicy:...

Auto-created alarms:
  AlarmHigh: TargetTracking-demo-web-asg-AlarmHigh-7cd8afbb-...
  AlarmLow:  TargetTracking-demo-web-asg-AlarmLow-173efae5-...

→ One put-scaling-policy command = policy + 2 CloudWatch alarms + auto-scaling logic
→ No manual alarm configuration needed
```

### Predefined metric types for target tracking

| PredefinedMetricType | What it tracks | Use when |
|---|---|---|
| `ASGAverageCPUUtilization` | Average CPU across all instances | General purpose — most common choice |
| `ASGAverageNetworkIn` | Average bytes received per instance | Network-bound workloads (streaming, file uploads) |
| `ASGAverageNetworkOut` | Average bytes sent per instance | Network-bound workloads (API responses, downloads) |
| `ALBRequestCountPerTarget` | Requests per target from the ALB | Web apps — scale by traffic volume, not CPU |

``` bash
# Example: scale based on requests per target (needs ALB target group ARN)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name demo-web-asg \
  --policy-name requests-per-target-1000 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ALBRequestCountPerTarget",
      "ResourceLabel": "app/demo-web-alb/xxxxx/targetgroup/demo-web-tg/xxxxx"
    },
    "TargetValue": 1000.0
  }' \
  --profile demo
```

### Step scaling (more granular control)

Define explicit thresholds and actions — you control exactly how many instances to add at each level:

``` bash
# First create a CloudWatch alarm that triggers the policy
aws cloudwatch put-metric-alarm \
  --alarm-name demo-cpu-high-70 \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=AutoScalingGroupName,Value=demo-web-asg \
  --profile demo

# Then create the step scaling policy
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name demo-web-asg \
  --policy-name cpu-step-scale-out \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[
    {"MetricIntervalLowerBound": 0, "MetricIntervalUpperBound": 20, "ScalingAdjustment": 1},
    {"MetricIntervalLowerBound": 20, "ScalingAdjustment": 3}
  ]' \
  --profile demo
```

- If CPU > 70% → add 1 instance.
- If CPU > 90% (70+20) → add 3 instances.
- More control than target tracking, but more to configure.

| CPU level | Action | How the step adjustment reads |
|---|---|---|
| 70% – 90% | Add 1 instance | Lower bound 0, upper bound 20 (above the alarm threshold of 70) |
| > 90% | Add 3 instances | Lower bound 20, no upper bound (20+ above threshold) |
| < 30% | Remove 1 instance | Separate scale-in policy (not shown) |

### Scheduled scaling

Scale based on time, not metrics. Good for predictable traffic patterns:

``` bash
# Scale up to 3 instances at 8am Dhaka time (2am UTC) on weekdays
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name demo-web-asg \
  --scheduled-action-name morning-scale-up \
  --recurrence "0 2 * * MON-FRI" \
  --desired-capacity 3 \
  --profile demo

# Scale back to 1 instance at 10pm Dhaka time (4pm UTC) on weekdays
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name demo-web-asg \
  --scheduled-action-name evening-scale-down \
  --recurrence "0 16 * * MON-FRI" \
  --desired-capacity 1 \
  --profile demo

# List scheduled actions
aws autoscaling describe-scheduled-actions \
  --auto-scaling-group-name demo-web-asg \
  --query "ScheduledUpdateGroupActions[].{Name:ScheduledActionName,Recurrence:Recurrence,Desired:DesiredCapacity}" \
  --output table \
  --profile demo

# Delete a scheduled action
aws autoscaling delete-scheduled-action \
  --auto-scaling-group-name demo-web-asg \
  --scheduled-action-name morning-scale-up \
  --profile demo
```

!!! note "Cron format"

    The recurrence uses cron syntax: `minute hour day-of-month month day-of-week`. All times are UTC. Dhaka is UTC+6, so 8am Dhaka = 2am UTC.

### Scale-in protection

Prevents specific instances from being terminated during scale-in. Use for instances running long jobs that shouldn't be interrupted:

``` bash
# Protect a specific instance
aws autoscaling set-instance-protection \
  --auto-scaling-group-name demo-web-asg \
  --instance-ids i-xxxxx \
  --protected-from-scale-in \
  --profile demo

# Remove protection
aws autoscaling set-instance-protection \
  --auto-scaling-group-name demo-web-asg \
  --instance-ids i-xxxxx \
  --no-protected-from-scale-in \
  --profile demo
```

### Which policy type to choose?

| Policy type | Complexity | Best for | You manage |
|---|---|---|---|
| **Target tracking** | Simplest | Most workloads — set target, AWS handles the rest | Just the target value |
| **Step scaling** | Medium | Workloads with sudden spikes — need different responses at different levels | Alarms + step adjustments |
| **Scheduled** | Simplest | Predictable traffic patterns — business hours, batch windows | Cron schedules + desired counts |
| **Combined** | Most complex | Production — scheduled as baseline + target tracking for unexpected spikes | All of the above |

!!! success "Start here"

    - For the ramp plan, target tracking on CPU is enough.
    - Add step scaling or scheduled scaling only if Manager asks "what would you do for a flash sale?"
    - That's when you'd combine scheduled (pre-scale before the sale) + target tracking (handle unexpected spikes during).

### Manage scaling policies

``` bash
# List all policies on an ASG
aws autoscaling describe-policies \
  --auto-scaling-group-name demo-web-asg \
  --query "ScalingPolicies[].{Name:PolicyName,Type:PolicyType,Target:TargetTrackingConfiguration.TargetValue}" \
  --output table \
  --profile demo

# Delete a scaling policy
aws autoscaling delete-policy \
  --auto-scaling-group-name demo-web-asg \
  --policy-name cpu-target-60 \
  --profile demo

# Note: deleting a target tracking policy also deletes its auto-created CloudWatch alarms
```
