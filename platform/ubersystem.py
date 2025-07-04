import json
import pulumi
import pulumi_aws as aws

import eks

config = pulumi.Config()

role = aws.iam.Role("uber-email",
    name = "uber-email",
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

policy = aws.iam.Policy("uber-email",
    name="uber-email",
    path="/",
    description="Allow sending emails as magfest.org",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowSendingEmail",
                "Effect": "Allow",
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                "Resource": [
                    "arn:aws:ses:*:278110951434:configuration-set/*",
                    "arn:aws:ses:*:278110951434:identity/magfest.org"
                ]
            }
        ]
    }))

for namespace in config.require_object("uber_instances"):
    aws.eks.PodIdentityAssociation(f"uber_email_{namespace}",
        cluster_name=eks.eks_cluster.name,
        namespace=namespace,
        service_account="ubersystem-email",
        role_arn=role.arn)