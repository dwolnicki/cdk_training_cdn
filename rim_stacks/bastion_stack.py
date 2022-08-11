from aws_cdk import (
    Stack,
    aws_ec2 as ec2,    
    aws_iam as iam,    
    CfnOutput   

)
from constructs import Construct

class RimBastionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, owner: str, vpc: ec2.Vpc, bastion_sec_grp: ec2.SecurityGroup, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        key_name = self.node.try_get_context("EC2KeyName")

        instance_type_name = 't3a.nano'
        volume_size = 8            

        instance_name = owner+'-bastion-host'
        ami_name      = 'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20220420'     
        ami_image     = ec2.MachineImage().lookup(name=ami_name)
        instance_type = ec2.InstanceType(instance_type_name)        

        iam_role = iam.Role(self, owner+'-bastion-role',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies = [ 
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMPatchAssociation'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'),
            ],
            role_name = owner+'-bastion-role',            
        )        

        user_data = ec2.UserData.custom("""#!/bin/bash
            apt-get update
            apt-get -y install net-tools awscli
            echo bastion > /etc/hostname
            sysctl kernel.hostname = bastion"""
        )           

        self.bastion_host = ec2.Instance(self, owner+'bastion_host', 
            instance_name=instance_name,
            instance_type=instance_type,
            machine_image=ami_image,
            vpc=vpc,
            role = iam_role,
            security_group=bastion_sec_grp,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            user_data=user_data,
            key_name = key_name          
        )              

        bastion_elastic_ip = ec2.CfnEIP(self, owner+'elastic_ip',
            instance_id = self.bastion_host.instance_id
        )   

        CfnOutput(self, owner+'output-bastion-eip',
            value = bastion_elastic_ip.ref
        )        

