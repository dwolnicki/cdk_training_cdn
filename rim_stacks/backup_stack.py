from aws_cdk import (
    Duration,
    Stack,
    aws_ec2 as ec2,    
    aws_s3 as s3,
    aws_backup as backup,   
    RemovalPolicy,
    aws_iam as iam,   
    aws_events as events,      
)
from constructs import Construct

class RimBackupStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, owner: str, bastion_host: ec2.Instance, bucket: s3.Bucket,  **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        backup_vault = backup.BackupVault(self, owner+'-backup-vault',
            backup_vault_name = owner+'-backup-vault',
            removal_policy = RemovalPolicy.DESTROY,
        )   
        

        backup_iam_role = iam.Role(self, owner+'-backup-role',
            assumed_by=iam.ServicePrincipal('backup.amazonaws.com'),
            managed_policies = [ 
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForBackup'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AWSBackupServiceRolePolicyForS3Backup'),
            ],
            role_name = owner+'-backup-role',            
        )       

        restore_iam_role = iam.Role(self, owner+'-restore-role',
            assumed_by=iam.ServicePrincipal('backup.amazonaws.com'),
            managed_policies = [ 
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForRestores'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AWSBackupServiceRolePolicyForS3Restore')
            ],
            role_name = owner+'-restore-role',            
        ) 
        
        restore_iam_role.attach_inline_policy(
            policy = iam.Policy(self, owner+'-iam-passrole-policy',
                document = iam.PolicyDocument(
                    statements = [
                        iam.PolicyStatement(
                            actions=["iam:PassRole"],
                            resources=["*"]
                        )
                    ]
                )
            )
        ) 
        
        ec2_backup_plan = backup.BackupPlan(self, owner+'-backup-plan',
            backup_plan_name = owner+'-backup-plan',
            backup_vault = backup_vault,
            backup_plan_rules = [
                backup.BackupPlanRule(
                    rule_name = owner+'-backup-rule01',
                    schedule_expression = events.Schedule.cron(
                        hour = '4',
                        minute = '10'
                    ),                    
                    start_window = Duration.hours(1),
                    completion_window = Duration.hours(4),
                    move_to_cold_storage_after = Duration.days(30),
                    delete_after = Duration.days(120),
                )
            ]
        )        

        ec2_backup_plan.add_selection(owner+'-bastion-selection',
            backup_selection_name = owner+'-bastion-selection',
            role = backup_iam_role,
            resources = [
                backup.BackupResource.from_ec2_instance(bastion_host)            
            ]            
        )       
        
        s3_backup_plan = backup.BackupPlan(self, owner+'-s3-backup-plan',
            backup_plan_name = owner+'-s3-backup-plan',
            backup_vault = backup_vault,
            backup_plan_rules = [
                backup.BackupPlanRule(
                    rule_name = owner+'-s3-backup-rule01',
                    start_window = Duration.hours(1),
                    completion_window = Duration.hours(4),
                    delete_after = Duration.days(30),
                    enable_continuous_backup = True,
                )
            ]
        )      
        
        s3_backup_plan.add_selection(owner+'-s3-bastion-selection',
            backup_selection_name = owner+'-s3-bastion-selection',
            role = backup_iam_role,
            resources = [
                backup.BackupResource.from_arn(bucket.bucket_arn)            
            ]            
        )             

