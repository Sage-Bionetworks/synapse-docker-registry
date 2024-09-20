# synapse-docker-registry

CDK-based template for deploying the Synapse Docker registry


## Configuration

We use the [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)

In dev the secret is named `registry-dev-DockerFargateStack/dev/ecs` and in the prod stack,
`registry-prod-DockerFargateStack/prod/ecs`

A secret is a collection of key-value pairs.  For this application there is just one pair.  The key should be `notification_auth` and the value is the
Base64 encoded "Basic auth" credentials which are a shared-secret with Synapse as the event notification recipient.


### Missing Secrets

Each new environment (dev/staging/prod/etc..) may require adding secrets.  If a
secret is not created for the environment you may get an error with the following stack trace:

```
Resource handler returned message: "Error occurred during operation 'ECS Deployment Circuit Breaker was triggered'." (RequestToken: d180e115-ba94-d8a2-acf9-abe17a3aaed9, HandlerErrorCode: GeneralServiceException)
    new BaseService (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/jsii-kernel-4PEWmj/node_modules/aws-cdk-lib/aws-ecs/lib/base/base-service.js:1:3583)
    \_ new FargateService (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/jsii-kernel-4PEWmj/node_modules/aws-cdk-lib/aws-ecs/lib/fargate/fargate-service.js:1:967)
    \_ new ApplicationLoadBalancedFargateService (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/jsii-kernel-4PEWmj/node_modules/aws-cdk-lib/aws-ecs-patterns/lib/fargate/application-load-balanced-fargate-service.js:1:2300)
    \_ Kernel._create (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/tmpqkmckdm2/lib/program.js:9964:29)
    \_ Kernel.create (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/tmpqkmckdm2/lib/program.js:9693:29)
    \_ KernelHost.processRequest (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/tmpqkmckdm2/lib/program.js:11544:36)
    \_ KernelHost.run (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/tmpqkmckdm2/lib/program.js:11504:22)
    \_ Immediate._onImmediate (/private/var/folders/qr/ztb40vmn2pncyh8jpsgfnrt40000gp/T/tmpqkmckdm2/lib/program.js:11505:46)
    \_ processImmediate (node:internal/timers:464:21)
```


## Testing

### Static Analysis
As a pre-deployment step we syntatically validate the CDK json, yaml and
python files with [pre-commit](https://pre-commit.com).

Please install pre-commit, once installed the file validations will
automatically run on every commit.  Alternatively you can manually
execute the validations by running `pre-commit run --all-files`.

### Python Tests
Tests are available in the tests folder. Execute the following to run tests:

```
python -m pytest tests/ -s -v
```
