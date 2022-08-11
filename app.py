#!/usr/bin/env python3
import os

import aws_cdk as cdk

from dotenv import load_dotenv

from rim_stacks.vpc_stack import RimVpcStack
from rim_stacks.elb_app_stack import RimElbAppStack
from rim_stacks.bastion_stack import RimBastionStack
from rim_stacks.cloudfront_stack import RimCloudFrontStack
from rim_stacks.monitoring_stack import RimMonitoringStack
from rim_stacks.backup_stack import RimBackupStack

load_dotenv()

owner = os.getenv('OWNER')
rim_hosted_zone_name = os.getenv('RIM_HOSTED_ZONE_NAME')
webapp_token = os.getenv('WEBAPP_TOKEN')
email = os.getenv('EMAIL')




app = cdk.App()


creator = app.node.try_get_context("Creator")
project = app.node.try_get_context("Project")


#dodam dwa tagi ktore beda dodawane do wszystkich resource w mojej aplikacji
cdk.Tags.of(app).add("Creator", creator)
cdk.Tags.of(app).add("Project", project)


rimVpc = RimVpcStack(app, owner.capitalize()+"RimVpcStack",
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    owner=owner

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

rimElbApp = RimElbAppStack(app, owner.capitalize()+"RimElbAppStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    owner=owner,
    vpc = rimVpc.vpc,
    web_srv_sec_grp = rimVpc.web_srv_sec_grp,
    alb_sec_grp = rimVpc.alb_sec_grp,
    webapp_token = webapp_token,
    rim_hosted_zone_name = rim_hosted_zone_name
)

rimBastion = RimBastionStack(app, owner.capitalize()+"RimBastionStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    owner=owner,
    vpc = rimVpc.vpc,
    bastion_sec_grp = rimVpc.bastion_sec_grp
)

rimCloudFront = RimCloudFrontStack(app, owner.capitalize()+"RimCloudFrontStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region='us-east-1'),
    owner=owner,
    webapp_token = webapp_token,
    rim_hosted_zone_name = rim_hosted_zone_name
)

rimMonitoring = RimMonitoringStack(app, owner.capitalize()+"RimMonitoringStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    owner=owner,
    alb = rimElbApp.alb,
    asg = rimElbApp.asg,
    email = email
)

rimBackup = RimBackupStack(app, owner.capitalize()+"RimBackupStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    owner=owner,
    bastion_host = rimBastion.bastion_host,
    bucket = rimElbApp.bucket

)

app.synth()
