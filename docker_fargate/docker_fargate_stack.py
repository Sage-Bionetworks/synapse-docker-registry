from aws_cdk import (Stack,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as r53,
    aws_iam as iam,
    CfnOutput,
    Duration,
    Tags)

import config as config
import aws_cdk.aws_certificatemanager as cm
import aws_cdk.aws_secretsmanager as sm
from constructs import Construct
from docker_fargate.generate_ssl_cert import cert_gen

from aws_cdk.aws_ecr_assets import Platform

ACM_CERT_ARN_CONTEXT = "ACM_CERT_ARN"
IMAGE_PATH_AND_TAG_CONTEXT = "IMAGE_PATH_AND_TAG"
PORT_NUMBER_CONTEXT = "PORT"

# The name of the environment variable that will hold the secrets
SECRETS_MANAGER_ENV_NAME = "SECRETS_MANAGER_SECRETS"
CONTAINER_ENV_NAME = "CONTAINER_ENV"

PRIVATE_KEY_FILE_NAME = "privatekey.pem"
CERTIFICATE_FILE_NAME = "certificate.pem"

BUCKET_NAME = "BUCKET_NAME"

NOTIFICATION_AUTH_SECRET_JSON_KEY="notification_auth"
HTTP_SECRET_SECRET_JSON_KEY="http_secret"

def get_secret(scope: Construct, id: str, name: str) -> str:
    return sm.Secret.from_secret_name_v2(scope, id, name)
    # see also: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_ecs/Secret.html
    # see also: ecs.Secret.from_ssm_parameter(ssm.IParameter(parameter_name=name))

def get_container_env(env: dict) -> dict:
    return env.get(CONTAINER_ENV_NAME, {})

def get_bucket_name(env: dict) -> dict:
    return env.get(BUCKET_NAME)

def get_certificate_arn(env: dict) -> str:
    return env.get(ACM_CERT_ARN_CONTEXT)

def get_docker_image_name(env: dict):
    return env.get(IMAGE_PATH_AND_TAG_CONTEXT)

def get_port(env: dict) -> int:
    return int(env.get(PORT_NUMBER_CONTEXT))

class DockerFargateStack(Stack):

    def __init__(self, scope: Construct, context: str, env: dict, vpc: ec2.Vpc, **kwargs) -> None:
        stack_prefix = f'{env.get(config.STACK_NAME_PREFIX_CONTEXT)}'
        stack_id = f'{stack_prefix}-DockerFargateStack'
        super().__init__(scope, stack_id, **kwargs)

        # set up the bucket
        bucket_name=get_bucket_name(env)
        bucket_arn=f"arn:aws:s3:::{bucket_name}"
        bucket=s3.Bucket.from_bucket_attributes(self, id=bucket_name, bucket_arn=bucket_arn)

        #
        # Docker Registry cannot access the task role provided by
        # ECS.  The work-around is to define an IAM user, give the
        # user bucket access, and pass its key pair to the container
        # as environment variables.
        #

        # create a user
        user = iam.User(self, "DockerRegistryUser")
        # create a key pair, storing the secret in Secret Manager
        access_key = iam.AccessKey(self, "AccessKey", user=user)
        secret_stored_name = f'{env.get(config.STACK_NAME_PREFIX_CONTEXT)}-DockerFargateStack/{context}/access_key'
        secret_stored_access_key = sm.Secret(self, secret_stored_name,
            secret_string_value=access_key.secret_access_key
        )

        # give the user S3 access
        bucket.grant_read_write(user)

        cluster = ecs.Cluster(
            self,
            f'{stack_id}-Cluster',
            vpc=vpc,
            container_insights=True)

        secret_name = f'{env.get(config.STACK_NAME_PREFIX_CONTEXT)}-DockerFargateStack/{context}/ecs'
        sm_secret = get_secret(self, secret_name, secret_name)
        secrets = {
            NOTIFICATION_AUTH_SECRET_JSON_KEY:
                ecs.Secret.from_secrets_manager(sm_secret, NOTIFICATION_AUTH_SECRET_JSON_KEY),
            HTTP_SECRET_SECRET_JSON_KEY:
                ecs.Secret.from_secrets_manager(sm_secret, HTTP_SECRET_SECRET_JSON_KEY),
            "AWS_SECRET_ACCESS_KEY": ecs.Secret.from_secrets_manager(secret_stored_access_key)
        }

        env_vars = get_container_env(env)
        env_vars[BUCKET_NAME]=bucket_name
        env_vars["AWS_ACCESS_KEY_ID"]=access_key.access_key_id

        # Build the container image for the registry
        # Need self-signed certificates to add to the image
        key_and_cert = cert_gen()
        # write the private key and self-signed-cert to disk for Docker to use
        with open(PRIVATE_KEY_FILE_NAME, "wt") as f:
          f.write(key_and_cert["private_key"])
        with open(CERTIFICATE_FILE_NAME, "wt") as f:
          f.write(key_and_cert["certificate"])
        # Now build the image, using the self-signed cert and key
        image = ecs.ContainerImage.from_asset(
            directory=".",
            platform=Platform.LINUX_AMD64, # important to include when building locally, for testing
            build_args={"stack":context} # 'dev' or 'prod'
        )

        # default ECS execution policy plus Guardduty access
        execution_role = iam.Role(
            self,
            "ExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            )
        )

        task_image_options = ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                   image=image,
                   environment=env_vars,
                   secrets = secrets,
                   container_port = get_port(env),
                   execution_role=execution_role)

        cert = cm.Certificate.from_certificate_arn(
            self,
            f'{stack_id}-Certificate',
            get_certificate_arn(env),
        )

        load_balanced_fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            f'{stack_prefix}-Service',
            cluster=cluster,            # Required
            cpu=2048,                   # Default is 256
            desired_count=2,            # Number of copies of the 'task' (i.e. the app') running behind the ALB
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True), # Enable rollback on deployment failure
            task_image_options=task_image_options,
            memory_limit_mib=4096,      # Default is 512
            public_load_balancer=True,  # Default is False
            redirect_http=True,
            # TLS:
            target_protocol=elbv2.ApplicationProtocol.HTTPS,
            certificate=cert,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            ssl_policy=elbv2.SslPolicy.FORWARD_SECRECY_TLS12_RES # Strong forward secrecy ciphers and TLS1.2 only.
        )

        scalable_target = load_balanced_fargate_service.service.auto_scale_task_count(
           min_capacity=2, # Minimum capacity to scale to. Default: 1
           max_capacity=4 # Maximum capacity to scale to.
        )

        # Add more capacity when CPU utilization reaches 50%
        scalable_target.scale_on_cpu_utilization("CpuScaling",
            target_utilization_percent=50
        )

        # Add more capacity when memory utilization reaches 50%
        scalable_target.scale_on_memory_utilization("MemoryScaling",
            target_utilization_percent=50
        )

        # Tag all resources in this Stack's scope with context tags
        for key, value in env.get(config.TAGS_CONTEXT).items():
            Tags.of(scope).add(key, value)

        # Export load balancer name
        lb_dns_name = load_balanced_fargate_service.load_balancer.load_balancer_dns_name
        lb_dns_export_name = f'{stack_id}-LoadBalancerDNS'
        CfnOutput(self, 'LoadBalancerDNS', value=lb_dns_name, export_name=lb_dns_export_name)
