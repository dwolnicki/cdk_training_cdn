import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_training_cdn.cdk_training_cdn_stack import CdkTrainingCdnStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_training_cdn/cdk_training_cdn_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkTrainingCdnStack(app, "cdk-training-cdn")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
