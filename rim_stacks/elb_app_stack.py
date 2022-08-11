from aws_cdk import (
    Duration,
    Stack,
    aws_ec2 as ec2,    
    aws_elasticloadbalancingv2 as elbv2,    
    aws_iam as iam,
    aws_s3 as s3,    
    RemovalPolicy,
    aws_s3_deployment as s3_deployment,
    aws_autoscaling as autoscaling,
    aws_route53 as route53,    
    aws_certificatemanager as acm, 
    aws_route53_targets as route53_targets,   
)
from constructs import Construct

class RimElbAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, owner: str, vpc: ec2.Vpc, web_srv_sec_grp: ec2.SecurityGroup, alb_sec_grp: ec2.SecurityGroup, webapp_token: str, rim_hosted_zone_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        instance_type_name = 't3a.nano'
        volume_size = 8
        subnet_type=ec2.SubnetType.PUBLIC
        min_capacity = 1
        max_capacity = 4 
        target_utilization_percent = 30         
        health_check = elbv2.HealthCheck(
            healthy_threshold_count = 2,
            unhealthy_threshold_count = 2,
            timeout = Duration.seconds(5),
            interval = Duration.seconds(10),
            healthy_http_codes = "200"
        )          


        instance_name = owner+'-webapp-instance'
        ami_name      = 'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20220420'     
        ami_image     = ec2.MachineImage.lookup(name=ami_name)
        instance_type = ec2.InstanceType(instance_type_name)        

        iam_role = iam.Role(self, owner+'-webapp-role',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies = [ 
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMPatchAssociation'),
            ],            
        )            

        self.bucket = s3.Bucket(self, owner+'-bucket',
            versioned = True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            auto_delete_objects = True,
            removal_policy = RemovalPolicy.DESTROY
        )

        bucket_deployment = s3_deployment.BucketDeployment(self, owner+'s3-deployment',
            destination_bucket = self.bucket,
            sources = [s3_deployment.Source.asset('files/s3')]
        )
        
        user_data = ec2.UserData.custom("""#!/bin/bash
            apt-get update
            apt-get -y install apache2 awscli
            aws s3 sync s3://%s/ /var/www/html/
            systemctl restart apache2
            systemctl enable apache2"""%self.bucket.bucket_name
        )  

        lt = ec2.LaunchTemplate(self, owner+'-lt',
            instance_type=instance_type,
            machine_image=ami_image,
            role=iam_role,            
            security_group=web_srv_sec_grp,        
            user_data=user_data,
            block_devices = [
                ec2.BlockDevice(
                    device_name = '/dev/sda1',
                    mapping_enabled = True,
                    volume = ec2.BlockDeviceVolume.ebs(
                        volume_size = volume_size,
                        volume_type = ec2.EbsDeviceVolumeType.GP3,
                        iops = 3000
                    )
                )
            ]
        )
        
        self.asg = autoscaling.AutoScalingGroup(self, owner+'-asg',
            vpc=vpc,
			vpc_subnets=ec2.SubnetSelection(
                subnet_type=subnet_type
            ), 
            launch_template = lt,
			min_capacity = min_capacity,
			max_capacity = max_capacity,
            group_metrics=[
                autoscaling.GroupMetrics(autoscaling.GroupMetric.IN_SERVICE_INSTANCES)
            ]
		)

        self.asg.scale_on_cpu_utilization(owner+' Target Tracking Policy',
            target_utilization_percent = target_utilization_percent,
            estimated_instance_warmup = Duration.seconds(240)
        )

        tg = elbv2.ApplicationTargetGroup(self, owner+'-tg',
            target_type = elbv2.TargetType.INSTANCE,
            vpc = vpc,
            port = 80,
            health_check = health_check
        )

        self.asg.attach_to_application_target_group(tg)        

        self.alb = elbv2.ApplicationLoadBalancer(self, owner+'-alb',
            vpc=vpc,
			vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),            
            internet_facing=True,
            security_group=alb_sec_grp, 
        )        

        #listener_http = self.alb.add_listener("HTTP Listener", port=80)

        #listener_http.add_target_groups(owner+'-targets',
        #   target_groups = [tg],
        #    priority=10,            
        #    conditions = [
        #        elbv2.ListenerCondition.http_header(
        #            name = 'X-Custom-Header',
        #            values = [webapp_token]
        #        ),
        #    ]
        #)

        #listener_http.add_action("DefaultAction",
        #    action = elbv2.ListenerAction.fixed_response(
        #        status_code = 403,
        #        message_body = '<html><h1>403 Forbidden</h1></html>',
        #        content_type = 'text/html'        
        #    )
        #) 
        
        my_zone = route53.HostedZone.from_lookup(self, owner+'-dns-zone',
            domain_name = rim_hosted_zone_name
        )           

        cert_elb = acm.Certificate(self, owner+'-elb-cert',
            domain_name = owner.lower()+'.elb.aws.'+rim_hosted_zone_name,
            validation = acm.CertificateValidation.from_dns(my_zone)
        )

        listener_https = self.alb.add_listener("HTTPS Listener", 
            port=443,
            certificates = [elbv2.ListenerCertificate(cert_elb.certificate_arn)]
        )        

        listener_https.add_target_groups(owner+' targets',
            target_groups = [tg],
            priority=10,            
            conditions = [
                elbv2.ListenerCondition.http_header(
                    name = 'X-Custom-Header',
                    values = [webapp_token]
                ),
            ]
        )

        listener_https.add_action("DefaultAction",
            action = elbv2.ListenerAction.fixed_response(
                status_code = 403,
                message_body = '<html><h1>403 Forbidden</h1></html>',
                content_type = 'text/html'
            )
        )        

        alb_dns = route53.ARecord(self, owner+'-alb-dns-record',
            zone = my_zone,
            target = route53.RecordTarget.from_alias(
                route53_targets.LoadBalancerTarget(self.alb)
            ),
            record_name = owner.lower()+'.elb.aws.'+rim_hosted_zone_name
        )        
        
        
