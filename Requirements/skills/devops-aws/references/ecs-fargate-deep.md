# ECS Fargate — Deep Reference

Production-grade ECS Fargate patterns. Loaded automatically when working on
ECS task definitions, services, or auto-scaling.

## Task Definition: the right defaults

```json
{
  "family": "<service>",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",                          // 0.25/0.5/1/2/4/8/16 vCPU
  "memory": "2048",                       // matched to CPU per AWS table
  "runtimePlatform": {
    "operatingSystemFamily": "LINUX",
    "cpuArchitecture": "ARM64"            // Graviton — ~20% cheaper, comparable perf
  },
  "executionRoleArn": "arn:aws:iam::<acct>:role/ecsTaskExecutionRole",
  "taskRoleArn":      "arn:aws:iam::<acct>:role/<service>-task-role",
  "ephemeralStorage": { "sizeInGiB": 21 },  // 21 default; up to 200 for batch jobs
  "containerDefinitions": [{
    "name": "<service>",
    "image": "<account>.dkr.ecr.<region>.amazonaws.com/<service>:<sha>",
    "essential": true,
    "portMappings": [{ "containerPort": 3000, "protocol": "tcp", "appProtocol": "http2" }],
    "environment": [
      { "name": "NODE_ENV", "value": "production" },
      { "name": "AWS_REGION", "value": "<region>" }
    ],
    "secrets": [
      { "name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:...:secret:database_url" },
      { "name": "JWT_SECRET",   "valueFrom": "arn:aws:secretsmanager:...:secret:jwt_secret" }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group":         "/ecs/<service>",
        "awslogs-region":        "<region>",
        "awslogs-stream-prefix": "<service>",
        "awslogs-create-group":  "true",
        "mode":                  "non-blocking",     // critical: don't block app on log emit
        "max-buffer-size":       "25m"
      }
    },
    "healthCheck": {
      "command":     ["CMD-SHELL", "wget -qO- http://localhost:3000/health || exit 1"],
      "interval":    30,
      "timeout":     5,
      "retries":     3,
      "startPeriod": 30                              // grace period for slow boots
    },
    "linuxParameters": {
      "initProcessEnabled": true,                    // tini: reaps zombie processes
      "capabilities": { "drop": ["ALL"] }            // least privilege
    },
    "ulimits": [{ "name": "nofile", "softLimit": 65536, "hardLimit": 65536 }],
    "stopTimeout": 30                                // SIGTERM grace before SIGKILL
  }]
}
```

## Service Definition: production-grade

```hcl
resource "aws_ecs_service" "service" {
  name                              = "<service>"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.service.arn
  desired_count                     = var.min_tasks
  launch_type                       = "FARGATE"
  platform_version                  = "LATEST"      # auto-upgrades; pin only if reproducibility critical
  enable_execute_command            = true          # ECS Exec for debug
  propagate_tags                    = "SERVICE"
  health_check_grace_period_seconds = 60            # ALB health check grace
  deployment_maximum_percent        = 200           # blue/green needs 2x during shift
  deployment_minimum_healthy_percent = 100          # never below desired during deploy
  
  deployment_controller { type = "CODE_DEPLOY" }    # blue/green via CodeDeploy

  network_configuration {
    subnets          = var.private_subnet_ids       # private only — no public IP
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn   # CodeDeploy swaps blue↔green
    container_name   = "<service>"
    container_port   = 3000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.service.arn
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 70                          # 70% on-demand
    base              = 2                           # min 2 on-demand for HA
  }
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 30                          # 30% spot — for cost; not for stateful workloads
  }

  lifecycle {
    ignore_changes = [task_definition, load_balancer, desired_count]   # CodeDeploy manages these
  }
}
```

## Auto-Scaling: target tracking + step scaling

```hcl
resource "aws_appautoscaling_target" "service" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = 2
  max_capacity       = 20
}

# CPU target tracking (smooth)
resource "aws_appautoscaling_policy" "cpu" {
  name               = "<service>-cpu-tt"
  service_namespace  = aws_appautoscaling_target.service.service_namespace
  resource_id        = aws_appautoscaling_target.service.resource_id
  scalable_dimension = aws_appautoscaling_target.service.scalable_dimension
  policy_type        = "TargetTrackingScaling"
  target_tracking_scaling_policy_configuration {
    target_value       = 60.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_in_cooldown  = 300       # 5 min — slow scale-in to avoid flapping
    scale_out_cooldown = 60        # 1 min — fast scale-out
  }
}

# Custom metric: scale on RPS per task (more accurate for I/O-bound services)
resource "aws_appautoscaling_policy" "rps_per_task" {
  name               = "<service>-rps"
  service_namespace  = aws_appautoscaling_target.service.service_namespace
  resource_id        = aws_appautoscaling_target.service.resource_id
  scalable_dimension = aws_appautoscaling_target.service.scalable_dimension
  policy_type        = "TargetTrackingScaling"
  target_tracking_scaling_policy_configuration {
    target_value     = 500.0      # target 500 RPS per task
    customized_metric_specification {
      metric_name = "RequestCountPerTarget"
      namespace   = "AWS/ApplicationELB"
      statistic   = "Sum"
      unit        = "None"
      dimensions {
        name  = "TargetGroup"
        value = aws_lb_target_group.blue.arn_suffix
      }
    }
  }
}
```

## ECS Exec (debug into a running task)

Required setup:
- Task role has `ssmmessages:CreateControlChannel`, `ssmmessages:CreateDataChannel`, `ssmmessages:OpenControlChannel`, `ssmmessages:OpenDataChannel`
- `enable_execute_command = true` on the service
- `linuxParameters.initProcessEnabled: true`

Use:
```bash
aws ecs execute-command \
  --cluster <cluster> \
  --task <task-arn> \
  --container <service> \
  --interactive \
  --command "/bin/sh"
```

ECS Exec is the only sanctioned way to shell into prod. Audit logs go to CloudWatch Logs (configure `executeCommandConfiguration` on the cluster).

## Capacity Provider Strategy: when to use spot

| Workload | Strategy |
|---|---|
| User-facing API (latency-sensitive) | 100% on-demand. SLO trumps cost. |
| Background workers (idempotent, retryable) | 70/30 on-demand/spot or 100% spot if backlog is OK |
| Batch jobs (one-shot, retryable) | 100% spot. Save big. |
| Stateful (databases — but you wouldn't run these on Fargate anyway) | n/a |

Spot interruptions: 2-min warning via SIGTERM → ECS sends to container → app must drain cleanly.

## Graviton (ARM64): default for new services

ARM64 Fargate is ~20% cheaper and often comparable performance. Most Node.js, Python, Go, Java code runs unchanged. Verify with:
- Multi-arch Docker build: `docker buildx build --platform linux/arm64,linux/amd64`
- Benchmark in staging
- Check that all native deps have ARM64 wheels/binaries

## Sidecars (use sparingly)

Common sidecars:
- **Envoy** for App Mesh — required if joining the mesh
- **AWS Distro for OpenTelemetry collector** for traces
- **Fluent Bit** if you need structured log shipping beyond CloudWatch agent

Do NOT sidecar:
- Background workers (run as a separate ECS service)
- Migrations (run as a one-shot ECS Task)
- Cache (use ElastiCache, not in-process)

## Common Pitfalls

- ❌ `awslogs` driver in **blocking** mode — app stalls when CloudWatch is slow
- ❌ Missing `stopTimeout` — app gets SIGKILL'd mid-flight, drops in-flight requests
- ❌ Health check too aggressive — flapping during cold starts; add `startPeriod`
- ❌ No `enable_execute_command` — can't debug prod issues
- ❌ Using public subnets for tasks — exposes attack surface; use private + NAT
- ❌ Not setting task `cpu/memory` to a valid combo — task fails to start
- ❌ Sharing the task execution role across services — IAM blast radius

## CloudWatch Container Insights

Enable at cluster level:
```hcl
resource "aws_ecs_cluster" "main" {
  name = "<env>-cluster"
  setting {
    name  = "containerInsights"
    value = "enhanced"      # "enhanced" includes per-task GPU + storage metrics
  }
}
```
$2.55/mo per task (enhanced) vs $1.50 (default). Worth it for production.
