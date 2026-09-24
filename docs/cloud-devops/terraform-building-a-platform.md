---
title: "Terraform: Building a Platform in Code (ALB, ASG, ACM, RDS, ECS)"
---

# Terraform: Building a Platform in Code (ALB, ASG, ACM, RDS, ECS)

Every resource a typical AWS platform needs — declared, not clicked.
Nothing new conceptually here: this is the language and workflow from
[Terraform Fundamentals](terraform-fundamentals.md) and
[Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md), applied
to the actual shape of a real platform. See
[Terraform: EKS, Worked Examples & Lambda](terraform-eks-and-lambda.md)
for the Kubernetes and serverless half of the same platform.

## ALB — Listeners and Rules in Code

The four-resource shape (load balancer, target group, listener,
listener rule) as a module, driven by a map so adding a second
path-routed service is a new map entry, not a new resource block.

``` hcl
resource "aws_lb" "app" {
  name               = "${var.name_prefix}-alb"
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "service" {
  for_each = var.services   # map(object({ port = number, health_check_path = string }))
  name     = "${var.name_prefix}-${each.key}-tg"
  port     = each.value.port
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  health_check { path = each.value.health_check_path }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.acm_certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service[var.default_service].arn
  }
}

resource "aws_lb_listener_rule" "path" {
  for_each     = { for k, v in var.services : k => v if k != var.default_service }
  listener_arn = aws_lb_listener.https.arn
  priority     = index(keys(var.services), each.key) + 1
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service[each.key].arn
  }
  condition {
    path_pattern { values = ["/${each.key}", "/${each.key}/*"] }
  }
}
```

!!! note "A live path-routing 404, encoded as a fixed pattern"

    The `path_pattern` values include both the exact path and the
    wildcard (`/bar` and `/bar/*`) — this fixes a real 404 seen when
    only the wildcard was configured, written once into the module
    instead of remembered per rule.

## Auto Scaling Group in Code

``` hcl
resource "aws_launch_template" "app" {
  name_prefix   = "${var.name_prefix}-"
  image_id      = var.golden_ami_id
  instance_type = var.instance_type
  vpc_security_group_ids = [aws_security_group.app.id]
  lifecycle { create_before_destroy = true }
}

resource "aws_autoscaling_group" "app" {
  name                = "${var.name_prefix}-asg"
  vpc_zone_identifier = var.private_subnet_ids
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity
  target_group_arns   = [aws_lb_target_group.service[var.default_service].arn]

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}

resource "aws_autoscaling_policy" "cpu_target" {
  name                   = "${var.name_prefix}-cpu-target"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"
  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 60
  }
}
```

!!! success "create_before_destroy earns its keep here"

    Changing `golden_ami_id` (a new Golden AMI baked elsewhere in the
    pipeline) replaces the launch template. Without
    `create_before_destroy` (see [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md)), the ASG would briefly
    reference a deleted template if the new one failed to create — with
    it, the new template exists before the old one is removed.

## ACM and Route 53 in Code

``` hcl
resource "aws_acm_certificate" "app" {
  domain_name       = var.domain_name
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.app.domain_validation_options : dvo.domain_name => dvo
  }
  zone_id = var.hosted_zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_route53_record" "app" {
  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}
```

!!! note "A manual CNAME wait, now self-completing"

    `aws_acm_certificate_validation` is what makes `apply` actually wait
    for DNS validation to finish before moving on — by hand, this is
    watching `describe-certificates` for `ISSUED`. Here it's one
    dependency edge, and it means `destroy` then `apply` from empty
    needs no manual pause at all.

## RDS with Parameter and Subnet Groups, Multi-AZ

``` hcl
resource "aws_db_subnet_group" "app" {
  name       = "${var.name_prefix}-db-subnets"
  subnet_ids = var.private_data_subnet_ids   # a distinct subnet tier from the app tier
}

resource "aws_db_parameter_group" "app" {
  family = "postgres16"
  parameter {
    name  = "log_min_duration_statement"
    value = "500"   # ms -- feeds the slow-query workflow
  }
}

resource "aws_db_instance" "primary" {
  identifier             = "${var.name_prefix}-db"
  engine                 = "postgres"
  engine_version         = "16.4"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  multi_az               = var.environment == "stg"   # Multi-AZ only where the deliverable calls for it
  db_subnet_group_name   = aws_db_subnet_group.app.name
  parameter_group_name   = aws_db_parameter_group.app.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  manage_master_user_password = true   # password generated and rotated in Secrets Manager -- see below
  lifecycle { prevent_destroy = true }
}
```

!!! danger "prevent_destroy is deliberate here, not everywhere"

    Every other resource in this module accepts `destroy` then `apply`
    from empty. The database is the one exception — real data must
    never disappear because a teardown script ran against the wrong
    workspace. Tearing down for real means removing this `lifecycle`
    block first, as an explicit, separate step (see [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md)).

## Secrets Referenced from Secrets Manager, Never Stored

`manage_master_user_password = true` above already keeps the RDS
password out of state and out of config entirely — AWS generates it and
stores it in Secrets Manager directly. The application still needs to
read that secret at runtime, without it ever appearing in a `.tf` file
or a plan.

``` hcl
data "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_db_instance.primary.master_user_secret[0].secret_arn
}

# passed to the app as an environment variable pointing at the secret ARN,
# never as the decrypted value -- the app fetches and decrypts it at boot
resource "aws_ecs_task_definition" "order_service" {
  # ...
  container_definitions = jsonencode([{
    name = "order-service"
    secrets = [
      { name = "DB_PASSWORD", valueFrom = aws_db_instance.primary.master_user_secret[0].secret_arn }
    ]
  }])
}
```

!!! danger "A data source that reads a secret still writes it to state"

    The `aws_secretsmanager_secret_version` data source above pulls the
    plaintext value into Terraform state the moment anything references
    its `secret_string` attribute — the same exposure covered in [State,
    Environments & Regions](terraform-state-environments-and-regions.md)'s
    warning about `sensitive` variables. Prefer passing the secret's
    **ARN** to the running service (as the ECS task definition does
    above) and letting the container fetch and decrypt it at boot, so
    the plaintext value never has a reason to pass through Terraform at
    all.

## A Reusable ECS Service Module

An ECS order service — task definition and all — as a module, so that a
second microservice is one more module call, not a copy-pasted block of
ECS resources.

``` hcl
# modules/ecs-service/variables.tf
variable "name" {}
variable "image" {}
variable "container_port" { type = number }
variable "cluster_arn" {}
variable "target_group_arn" {}
variable "desired_count" {
  type    = number
  default = 2
}

# modules/ecs-service/main.tf
resource "aws_ecs_task_definition" "this" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  container_definitions = jsonencode([{
    name  = var.name
    image = var.image
    portMappings = [{ containerPort = var.container_port }]
  }])
}

resource "aws_ecs_service" "this" {
  name            = var.name
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = var.name
    container_port   = var.container_port
  }
}

# root: adding a microservice is one block
module "order_service" {
  source            = "./modules/ecs-service"
  name              = "order-service"
  image             = "${var.ecr_repo_url}:order-service-latest"
  container_port    = 8080
  cluster_arn       = aws_ecs_cluster.main.arn
  target_group_arn  = aws_lb_target_group.service["order"].arn
}
```

!!! success "This is the payoff from module interface design"

    The module's interface (see [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md)) exposes exactly five
    inputs — everything about clusters, task CPU/memory defaults, and
    Fargate wiring stays inside the module. A second service, say
    `payments-service`, is a second `module` block with different
    values for those five inputs, not a second copy of the
    task-definition JSON.

---

## Code Samples

- `code_samples/terraform/day02-modules/` — the network/security/
  compute/loadbalancing module split referenced throughout this page
- `code_samples/terraform/ecs-alb/` — ALB, listeners and target group
  in front of an ECS service
- `code_samples/terraform/ecs-cluster-service/` — the reusable ECS
  service module itself
