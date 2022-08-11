from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,    
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,    
    aws_cloudwatch_actions as cloudwatch_actions
)
from constructs import Construct

class RimMonitoringStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, owner: str, alb: elbv2.ApplicationLoadBalancer, asg: autoscaling.AutoScalingGroup, email: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        dashboard = cloudwatch.Dashboard(self, owner+"CdnDashboard",
            dashboard_name=owner+"_CDN_Dashboard",
            end="end",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="start"
        )        

        elb_text_widget = cloudwatch.TextWidget(
            markdown="# ALB Metrics",
            width = 24
        )        

        elb_request_count_widget = cloudwatch.GraphWidget(
            title = "ALB Request Count",
            left = [ alb.metric_request_count(
                label = "ALB Request Count",
            )],
            legend_position = cloudwatch.LegendPosition.RIGHT,
            width = 6
        )      
        
        elb_active_connection_widget = cloudwatch.SingleValueWidget(
            title = "ALB Active connections",
            metrics = [
                alb.metric_active_connection_count(
                    label = "Active connections",
                    color = cloudwatch.Color.PURPLE
                ),
            ],
            width = 6,
            height = 6
        )        

        elb_fixed_responses_widget = cloudwatch.GraphWidget(
            title = "ALB Fixed Responses",
            left = [
                alb.metric_http_fixed_response_count(
                    label = "Fixed Responses",
                    color = cloudwatch.Color.RED
                ),
                
            ],
            legend_position = cloudwatch.LegendPosition.RIGHT,
            width = 12
        )

        elb_http_codes_widget = cloudwatch.GraphWidget(
            title = "ALB HTTP Codes",
            left = [
                alb.metric_http_code_target(
                    code = elbv2.HttpCodeTarget.TARGET_2XX_COUNT,
                    label = "2xx OK",
                    color = cloudwatch.Color.GREEN
                ),
                alb.metric_http_code_target(
                    code = elbv2.HttpCodeTarget.TARGET_4XX_COUNT,
                    label = "4xx User error",
                    color = "#ffbf00"
                ),                
                alb.metric_http_code_target(
                    code = elbv2.HttpCodeTarget.TARGET_5XX_COUNT,
                    label = "5xx Server error",
                    color = cloudwatch.Color.RED
                )                
            ],
            legend_position = cloudwatch.LegendPosition.RIGHT,
            width = 18
        )

        elb_target_error_widget = cloudwatch.GraphWidget(
            title = "ALB Target errors",
            left = [
                alb.metric_target_connection_error_count(
                    label = "Target Errors",
                    color = cloudwatch.Color.RED
                ),
                
            ],
            legend_position = cloudwatch.LegendPosition.RIGHT,
            width = 6
        )

        dashboard.add_widgets(elb_text_widget)
        dashboard.add_widgets(elb_request_count_widget, elb_active_connection_widget, elb_fixed_responses_widget)
        dashboard.add_widgets(elb_http_codes_widget, elb_target_error_widget)
        
        asg_text_widget = cloudwatch.TextWidget(
            markdown="# ASG Metrics",
            width = 24
        )

        asg_ec2_cpu_avg_metric = cloudwatch.Metric(
            namespace="AWS/EC2",
            dimensions_map={
                "AutoScalingGroupName": asg.auto_scaling_group_name
            },
            metric_name="CPUUtilization",
            color=cloudwatch.Color.BLUE
        )  

        asg_ec2_cpu_avg_widget = cloudwatch.GraphWidget(
            title = "ASG EC2 CPU Average",
            left = [ asg_ec2_cpu_avg_metric ],
            legend_position = cloudwatch.LegendPosition.RIGHT,
            width = 18
        )        

        asg_in_service_instances_metric = cloudwatch.Metric(
            namespace="AWS/AutoScaling",
            metric_name="GroupInServiceInstances",
            dimensions_map={
                "AutoScalingGroupName": asg.auto_scaling_group_name
            },
            color=cloudwatch.Color.BLUE,
            label = "In Service Instances",
        )  
        
        asg_in_service_instances_widget = cloudwatch.SingleValueWidget(
            title = "ASG In Service Instances",
            metrics = [ asg_in_service_instances_metric ],
            width = 6,
            height = 6            
        )        
        
        dashboard.add_widgets(asg_text_widget)
        dashboard.add_widgets(asg_ec2_cpu_avg_widget, asg_in_service_instances_widget)        

        sns_topic = sns.Topic(self, owner+"CdnTopic",
            topic_name = owner+"CdnTopic",
            display_name = owner+"CdnTopic"
        )

        sns_subscription = sns.Subscription(self, owner+"CdnSubscription",
            topic = sns_topic,
            protocol = sns.SubscriptionProtocol.EMAIL,
            endpoint = email,            
        )        

        asg_ec2_cpu_avg_alarm = cloudwatch.Alarm(self, owner+"asg_ec2_cpu_avg_alarm",
            alarm_name = owner+"asg_ec2_cpu_avg_alarm",
            metric=asg_ec2_cpu_avg_metric,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            threshold=70,
            evaluation_periods=1,            
        )        

        asg_ec2_cpu_avg_alarm.add_alarm_action(cloudwatch_actions.SnsAction(sns_topic))

        asg_in_service_instances_alarm = cloudwatch.Alarm(self, owner+"asg_in_service_instances_alarm",
            alarm_name = owner+"asg_in_service_instances_alarm",
            metric = asg_in_service_instances_metric,
            comparison_operator = cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
            threshold = 0,
            evaluation_periods = 1,
        )

        asg_in_service_instances_alarm.add_alarm_action(cloudwatch_actions.SnsAction(sns_topic))
