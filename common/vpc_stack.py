import config

from aws_cdk import (Stack,
    aws_ec2 as ec2,
    aws_s3 as s3,
    Tags)

from constructs import Construct

VPC_CIDR_CONTEXT= "VPC_CIDR"
FLOW_LOGS_BUCKET="sagebase-vpc-flow-logs-bucket-bucket-5lvxjv2gp37h"

class VpcStack(Stack):

    def __init__(self, scope: Construct, context: str, env: dict, **kwargs) -> None:
        stack_id = f'{env.get(config.STACK_NAME_PREFIX_CONTEXT)}-common'
        super().__init__(scope, stack_id, **kwargs)
        self.vpc = ec2.Vpc(self,
                           f'{stack_id}-vpc',
                           cidr=env.get(VPC_CIDR_CONTEXT),
                           max_azs=2)

        bucket_arn=f"arn:aws:s3:::{FLOW_LOGS_BUCKET}"
        bucket=s3.Bucket.from_bucket_attributes(self, id=FLOW_LOGS_BUCKET, bucket_arn=bucket_arn)
        self.vpc.add_flow_log(f"{stack_id}-FlowLogS3",destination=ec2.FlowLogDestination.to_s3(bucket=bucket))

        # Tag all resources in this Stack's scope with context tags
        for key, value in env.get(config.TAGS_CONTEXT).items():
            Tags.of(scope).add(key, value)
