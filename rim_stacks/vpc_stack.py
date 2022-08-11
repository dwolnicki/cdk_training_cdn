from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,    
    # aws_sqs as sqs,
)
from constructs import Construct

class RimVpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, owner: str,  **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        max_azs = 2
        nat_gateways = 0
        subnet_configuration=[
            ec2.SubnetConfiguration(name=owner.capitalize()+'Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
            ec2.SubnetConfiguration(name=owner.capitalize()+'Isolated', subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24)
        ]          

        self.vpc = ec2.Vpc(self, owner.capitalize()+'Vpc',
            cidr='10.0.0.0/16',
            max_azs = max_azs,
            nat_gateways = nat_gateways,
            subnet_configuration = subnet_configuration
        )
        
        
        self.web_srv_sec_grp = ec2.SecurityGroup(self, owner+'-webapp-sg', 
            vpc=self.vpc, 
            allow_all_outbound=True
        )
        
        self.web_srv_sec_grp.add_ingress_rule(
            peer=ec2.Peer.ipv4('0.0.0.0/0'), 
            description='SSH access', 
            connection=ec2.Port.tcp(22)    
        )     
        
        self.web_srv_sec_grp.add_ingress_rule(
            peer=ec2.Peer.ipv4('0.0.0.0/0'), 
            description='HTTP access', 
            connection=ec2.Port.tcp(80)
        )
        
        self.alb_sec_grp = ec2.SecurityGroup(self, owner+'-alb-sg', 
            vpc = self.vpc, 
            allow_all_outbound = True
        )

        self.alb_sec_grp.add_ingress_rule(
            peer = ec2.Peer.ipv4('0.0.0.0/0'), 
            description = 'HTTPS access', 
            connection = ec2.Port.tcp(443)      
        )    

        #self.alb_sec_grp.add_ingress_rule(
        #    peer = ec2.Peer.ipv4('0.0.0.0/0'), 
        #    description = 'HTTP access', 
        #    connection = ec2.Port.tcp(80)      
        #)
        
        self.bastion_sec_grp = ec2.SecurityGroup(self, owner+'-bastion-sg', 
            vpc=self.vpc, 
            allow_all_outbound=True
        )  

        self.bastion_sec_grp.add_ingress_rule(
            peer=ec2.Peer.ipv4('0.0.0.0/0'), 
            description='SSH access', 
            connection=ec2.Port.tcp(22)
        )    
