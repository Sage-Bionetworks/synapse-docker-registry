import config

from aws_cdk import (Stack,
    aws_ec2 as ec2,
    Tags)

from constructs import Construct

VPC_CIDR_CONTEXT= "VPC_CIDR"

def get_region(env: dict) -> str:
    return env.get("AWS_DEFAULT_REGION")

class VpcStack(Stack):

    def __init__(self, scope: Construct, context: str, env: dict, **kwargs) -> None:
        stack_id = f'{env.get(config.STACK_NAME_PREFIX_CONTEXT)}-common'
        region=get_region(env)
        super().__init__(scope, stack_id, env={"region":region}, **kwargs)
        self.vpc = ec2.Vpc(self,
                           f'{stack_id}-vpc',
                           cidr=env.get(VPC_CIDR_CONTEXT),
                           max_azs=2)

        # Create a VPE Endpoint to let the registry reach API Gateway
        self.vpc_endpoint = ec2.InterfaceVpcEndpoint(self, f'{stack_id}-VpcEndpoint',
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.execute-api"),
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection())

        # Tag all resources in this Stack's scope with context tags
        for key, value in env.get(config.TAGS_CONTEXT).items():
            Tags.of(scope).add(key, value)
