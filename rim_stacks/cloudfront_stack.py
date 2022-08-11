from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,  
    aws_route53 as route53,
    aws_route53_targets as route53_targets,      
    aws_certificatemanager as acm,    
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,    
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    RemovalPolicy,
    aws_wafv2 as wafv2      
)
from constructs import Construct

class RimCloudFrontStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, owner: str, webapp_token: str, rim_hosted_zone_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        my_zone = route53.HostedZone.from_lookup(self, owner+'-dns-zone',
            domain_name = rim_hosted_zone_name
        )         
        
        cert_cloudfront = acm.Certificate(self, owner+'-cloudfront-cert',
            domain_name = owner.lower()+'.app.aws.'+rim_hosted_zone_name,
            validation = acm.CertificateValidation.from_dns(my_zone)
        )        

        oai = cloudfront.OriginAccessIdentity(self, owner+"-oai")

        bucket_alt = s3.Bucket(self, owner+'bucket-alt',
            versioned = True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            auto_delete_objects = True,
            removal_policy = RemovalPolicy.DESTROY
        )        

        bucket_alt_deployment = s3_deployment.BucketDeployment(self,  owner+'-s3-alt-deployment',
            destination_bucket = bucket_alt,
            sources = [s3_deployment.Source.asset('files/s3_alt')]
        )      
        

        waf_rule_rate = wafv2.CfnWebACL.RuleProperty(
            name = owner+'-waf-acl-rate-rule',
            priority=0,
            statement = wafv2.CfnWebACL.StatementProperty(
                rate_based_statement = wafv2.CfnWebACL.RateBasedStatementProperty(
                    aggregate_key_type = 'IP',
                    limit = 100,
                    # forwarded_ip_config =
                )
            ),
            action = wafv2.CfnWebACL.RuleActionProperty(
                block = wafv2.CfnWebACL.BlockActionProperty(
                    custom_response=wafv2.CfnWebACL.CustomResponseProperty(
                        response_code=403
                    )
                ),
            ),
            visibility_config = wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=owner+'-waf-acl-rate-rule',
                sampled_requests_enabled=True
            )                        
        )
        
        waf_rule_bot = wafv2.CfnWebACL.RuleProperty(
            name = owner+'-waf-acl-bot-rule',
            priority=1,
            statement = wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement = wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name = 'AWSManagedRulesBotControlRuleSet',
                    vendor_name = 'AWS'
                )
            ),
            override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
            visibility_config = wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=owner+'-waf-acl-bot-rule',
                sampled_requests_enabled=True
            )                        
        )
        
        waf_rule_aws_common = wafv2.CfnWebACL.RuleProperty(
            name = owner+'-waf-acl-aws-common-rule',
            priority=2,
            statement = wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement = wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name = 'AWSManagedRulesCommonRuleSet',
                    vendor_name = 'AWS'
                )
            ),
            override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
            visibility_config = wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=owner+'-waf-acl-aws-common-rule',
                sampled_requests_enabled=True
            )                        
        )

        waf_acl = wafv2.CfnWebACL(self, owner+'-waf-acl',
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            scope='CLOUDFRONT',
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=owner+'-waf-acl',
                sampled_requests_enabled=True
            ),            
            name = owner+'-waf-acl',
            rules = [ waf_rule_rate, waf_rule_bot, waf_rule_aws_common ]
        )
        
        cf = cloudfront.Distribution(self, owner+'-distribution',
            certificate = cert_cloudfront,
            default_root_object = 'index.html',
            domain_names = [owner.lower()+'.app.aws.'+rim_hosted_zone_name],
            price_class = cloudfront.PriceClass.PRICE_CLASS_100,
            geo_restriction=cloudfront.GeoRestriction.allowlist("PL", "DE", "NL", "LU"),
            web_acl_id = waf_acl.attr_arn,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.OriginGroup(
                    primary_origin = origins.HttpOrigin(
                        domain_name = owner.lower()+'.elb.aws.'+rim_hosted_zone_name,
                        custom_headers={
                            "X-Custom-Header": webapp_token
                        },
                    ),
                    fallback_origin = origins.S3Origin(
                        bucket = bucket_alt,
                        origin_access_identity = oai
                    ),
                    fallback_status_codes=[500, 502, 503, 504]
                )
            ),
            error_responses = [
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=404,
                    response_page_path="/error404.html"
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=403,
                    response_page_path="/error403.html"
                )                
            ]
        )   

        cf_dns = route53.ARecord(self, owner+'-cf-dns-record',
            zone = my_zone,
            record_name = owner.lower()+'.app.aws.'+rim_hosted_zone_name,
            target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(cf)),            
        )           