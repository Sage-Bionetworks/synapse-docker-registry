# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An AWS CDK (Python) app that deploys Synapse's Docker registry: the open source `registry:2` image, customized at synth time, running on ECS Fargate behind a public HTTPS ALB with WAF, storing images in an existing S3 bucket. Registry auth tokens come from Synapse, and push/pull events are sent back to Synapse's listener endpoint.

## Commands

```bash
pip install -r requirements.txt -r requirements-dev.txt

python -m pytest tests/ -s -v                                   # all tests
python -m pytest tests/unit/test_vpc_stack.py::test_vpc_created  # single test

pre-commit run --all-files    # static analysis (yamllint, check-json, check-ast, hadolint, git-secrets, ...)

cdk synth --context env=dev   # env must be "dev" or "prod" (config.CONTEXT_ENVS)
cdk deploy --context env=dev
```

`cdk synth` (and the unit tests) only stage the Docker build context; the image is built during `cdk deploy`, which requires Docker.

## Architecture

**Configuration flow.** `app.py` → `helpers.get_app_config()` reads `--context env=<dev|prod>` and returns that block from `cdk.json` (region, VPC CIDR, bucket name, ACM cert ARN, tags, stack name prefix). Both stacks take this dict as a parameter named `env`. It is **not** the CDK `Environment`; each stack builds its own `env={"region": ...}` for `super().__init__`. The stack constructor's second positional argument is the context name, not a construct id. Stack ids come from `STACK_NAME_PREFIX` (e.g. `registry-dev-common`, `registry-dev-DockerFargateStack`).

**Stacks.**
- `common/vpc_stack.py` (`VpcStack`) creates the VPC and an `execute-api` interface VPC endpoint.
- `docker_fargate/docker_fargate_stack.py` (`DockerFargateStack`, which depends on the VPC stack) creates:
  - the ALB Fargate service (2–4 tasks with CPU/memory autoscaling, HTTPS end to end)
  - WAF and ALB access logging
  - a private API Gateway + inline Lambda that logs registry notification events to CloudWatch, reachable only through the VPC endpoint
  - IAM key rotation

**Container image build.** During synth, `DockerFargateStack` calls `cert_gen()` (`docker_fargate/generate_ssl_cert.py`) and writes `privatekey.pem`/`certificate.pem` to the repo root (gitignored). It also calls `jwks_gen()` (`docker_fargate/generate_jwks.py`) to derive `resources/<context>/token_signing_jwks.json` (gitignored) from Synapse's token-signing cert `resources/<context>/token_signing_key_public_cert.pem`. Synapse's tokens name their signing key with a libtrust-style `kid`, which `registry:3` can only match through the `jwks` option. It then runs `ContainerImage.from_asset(".")` with build arg `stack=<context>`. The `Dockerfile` copies `resources/<stack>/config.yml` and the JWK Set into the image. The self-signed cert only encrypts ALB→container traffic (a HIPAA requirement); the ALB serves the ACM cert to clients.

**Runtime config templating.** `resources/<stack>/config.yml` holds literal placeholder tokens (`http_secret`, `notification_auth`, `api_gateway_url`, `bucket_name`). At container start, `startup.sh` replaces them with `sed`, using values from environment variables. If you add a templated value, you must update `config.yml` (both stacks), `startup.sh`, and the env/secrets passed in the stack. The dev and prod `config.yml` files differ only in the Synapse endpoint URLs and the token `service` name.

**Secrets.**
- Secrets Manager secret `<STACK_NAME_PREFIX>-DockerFargateStack/<context>/ecs` must already exist, holding the keys `notification_auth` and `http_secret`. It is not created by CDK. If it is missing, deploys fail with an "ECS Deployment Circuit Breaker was triggered" error.
- The registry can't use the ECS task role. Instead, the stack creates an IAM user with bucket read/write access and stores its access key in a CDK-managed secret, which is injected as `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.

**Key rotation (two Lambdas):**
1. Every 90 days, Secrets Manager invokes `docker_fargate/rotation_lambda`. It creates a new IAM key, tests it with STS, and promotes it to AWSCURRENT. It then stores the old key ID in the SSM parameter `/<prefix>/pending-key-deletion` and forces an ECS redeployment.
2. An EventBridge rule fires on ECS `SERVICE_STEADY_STATE` and triggers `docker_fargate/cleanup_lambda`, which deletes the old key named in SSM. The old key is only deleted after the new tasks are healthy.

## CI/CD

GitHub Actions (`.github/workflows/main.yml`) runs pre-commit, then pytest, then `cdk synth` for both dev and prod on every push and PR. **A push to the `dev` branch deploys to the dev AWS account. A push to the `prod` branch deploys to prod.**
