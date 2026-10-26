"""Offline-synthesizable deployment preparation; synthesizing never contacts AWS."""

from pathlib import Path

from aws_cdk import (
    Environment,
    App,
    CfnOutput,
    CfnParameter,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as deployment
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sqs as sqs
from constructs import Construct
from resonance.config import Settings


class ResonanceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str):
        super().__init__(
            scope, construct_id, env=Environment(region=Settings.from_env().aws_region)
        )
        ami = CfnParameter(
            self,
            "CoolAmiId",
            type="AWS::EC2::Image::Id",
            description="Subscribed COOL AMI that actually ships OpenCV 5",
        )
        prefix = CfnParameter(
            self,
            "CloudFrontPrefixListId",
            type="String",
            allowed_pattern="pl-[0-9a-f]+",
        )
        release_bucket = CfnParameter(self, "ReleaseBucket", type="String")
        release_key = CfnParameter(self, "ReleaseKey", type="String")
        email = CfnParameter(
            self, "BudgetEmail", type="String", allowed_pattern="[^@]+@[^@]+"
        )
        raw = s3.Bucket(
            self,
            "RawUploads",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(1),
                    noncurrent_version_expiration=Duration.days(1),
                    abort_incomplete_multipart_upload_after=Duration.days(1),
                )
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )
        evidence = s3.Bucket(
            self,
            "Evidence",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        web = s3.Bucket(
            self,
            "Web",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        table = dynamodb.Table(
            self,
            "Records",
            partition_key=dynamodb.Attribute(
                name="kind", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.RETAIN,
        )
        dlq = sqs.Queue(
            self,
            "DeadLetters",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            retention_period=Duration.days(14),
        )
        queue = sqs.Queue(
            self,
            "Measurements",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            visibility_timeout=Duration.minutes(15),
            dead_letter_queue=sqs.DeadLetterQueue(queue=dlq, max_receive_count=3),
        )
        topic = sns.Topic(self, "ApprovedInspections")
        vpc = ec2.Vpc(
            self,
            "Network",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="compute", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
            ],
        )
        role = iam.Role(
            self,
            "WorkerRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                )
            ],
        )
        raw.grant_read_write(role)
        evidence.grant_read_write(role)
        table.grant_read_write_data(role)
        queue.grant_consume_messages(role)
        queue.grant_send_messages(role)
        topic.grant_publish(role)
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    f"arn:aws:s3:::{release_bucket.value_as_string}/{release_key.value_as_string}"
                ],
            )
        )
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "set -euo pipefail",
            "mkdir -p /opt/resonance",
            f"aws s3 cp s3://{release_bucket.value_as_string}/{release_key.value_as_string} /opt/resonance/release.tar.gz",
            "tar -xzf /opt/resonance/release.tar.gz -C /opt/resonance",
            "cd /opt/resonance && bash infra/bootstrap.sh",
        )
        worker = ec2.Instance(
            self,
            "CoolWorker",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            instance_type=ec2.InstanceType("c7g.large"),
            machine_image=ec2.GenericLinuxImage({self.region: ami.value_as_string}),
            require_imdsv2=True,
            role=role,
            user_data=user_data,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(32, encrypted=True),
                )
            ],
        )
        worker.connections.allow_from(
            ec2.Peer.prefix_list(prefix.value_as_string),
            ec2.Port.tcp(8000),
            "CloudFront private origin only",
        )
        api_origin = origins.VpcOrigin.with_ec2_instance(
            worker,
            http_port=8000,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        )
        distribution = cloudfront.Distribution(
            self,
            "Edge",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(web),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "api/*": cloudfront.BehaviorOptions(
                    origin=api_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                ),
                "ws/*": cloudfront.BehaviorOptions(
                    origin=api_origin,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                ),
            },
        )
        if Path("web/dist").is_dir():
            deployment.BucketDeployment(
                self,
                "PublishConsole",
                sources=[deployment.Source.asset("web/dist")],
                destination_bucket=web,
                distribution=distribution,
                distribution_paths=["/*"],
            )
        group = logs.LogGroup(
            self,
            "Logs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.RETAIN,
        )
        group.grant_write(role)
        cloudwatch.Alarm(
            self,
            "DeadLetterAlarm",
            metric=dlq.metric_approximate_number_of_messages_visible(),
            threshold=1,
            evaluation_periods=1,
        )
        events.Rule(
            self,
            "StopOutsideJudging",
            schedule=events.Schedule.cron(hour="18", minute="0"),
            targets=[
                targets.AwsApi(
                    service="EC2",
                    action="stopInstances",
                    parameters={"InstanceIds": [worker.instance_id]},
                    policy_statement=iam.PolicyStatement(
                        actions=["ec2:StopInstances"],
                        resources=[
                            self.format_arn(
                                service="ec2",
                                resource="instance",
                                resource_name=worker.instance_id,
                            )
                        ],
                    ),
                )
            ],
        )
        budgets.CfnBudget(
            self,
            "Budget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(amount=20, unit="USD"),
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type="ACTUAL",
                        threshold=100,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            address=email.value_as_string, subscription_type="EMAIL"
                        )
                    ],
                )
            ],
        )
        for key, value in {
            "ConsoleUrl": f"https://{distribution.distribution_domain_name}",
            "InstanceId": worker.instance_id,
            "RawBucket": raw.bucket_name,
            "EvidenceBucket": evidence.bucket_name,
            "QueueUrl": queue.queue_url,
            "RecordsTable": table.table_name,
            "InspectionTopic": topic.topic_arn,
        }.items():
            CfnOutput(self, key, value=value)


app = App(outdir="outputs/cdk.out")
ResonanceStack(app, "Resonance")
app.synth()
