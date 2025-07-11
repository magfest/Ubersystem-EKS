import json
import pulumi
import pulumi_aws as aws

import eks

config = pulumi.Config()

use_rds = config.get("use_rds")
if not use_rds:
    role = aws.iam.Role("cnpg-backups",
        name = "cnpg-backups",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowCNPGToAssumeRoleForPodIdentity",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "pods.eks.amazonaws.com"
                    },
                    "Action": [
                        "sts:AssumeRole",
                        "sts:TagSession"
                    ]
                }
            ]
        }))

    policy = aws.iam.Policy("cnpg-backups",
        name="cnpg-backups",
        path="/",
        description="Allow backups to S3",
        policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
                {
                    "Sid": "AllowBackupsToS3",
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{config.require('postgres_backup_bucket')}/*",
                        f"arn:aws:s3:::{config.require('postgres_backup_bucket')}"
                    ]
                }
            ]
        }))

    aws.iam.RolePolicyAttachment("cnpg_policy",
        policy_arn=policy.arn,
        role=role.name)

    for namespace in config.require_object("uber_instances"):
        aws.eks.PodIdentityAssociation(f"cnpg_backups_{namespace}",
            cluster_name=eks.eks_cluster.name,
            namespace=namespace,
            service_account="database",
            role_arn=role.arn)
