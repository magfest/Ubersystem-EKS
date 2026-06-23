import json
import pulumi
import pulumi_aws as aws

import eks
import events_loader

config = pulumi.Config()

# MAGFest's SES identities are verified in this account; email policies grant
# access to identities here regardless of which account the cluster runs in.
SES_ACCOUNT = "278110951434"

# Trust policy shared by every per-instance role: EKS Pod Identity assumes it.
_ASSUME_ROLE_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowEKSToAssumeRoleForPodIdentity",
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
})


def _email_policy_document(identities):
    resources = [f"arn:aws:ses:*:{SES_ACCOUNT}:configuration-set/*"]
    resources += [f"arn:aws:ses:*:{SES_ACCOUNT}:identity/{identity}" for identity in identities]
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowSendingEmail",
                "Effect": "Allow",
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                "Resource": resources
            }
        ]
    })


def _lambda_policy_document(lambda_arns):
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowInvokingConfiguredLambdas",
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": lambda_arns
            }
        ]
    })


# Each event instance gets its own role so its SES identities and Lambda
# permissions are scoped to just that instance. Per-instance email identities
# and lambdas come from the server's stack config entry.
for server in events_loader.load_servers():
    namespace = server["name"]
    email_identities = server.get("email_identities") or ["magfest.org"]
    lambda_arns = server.get("lambdas") or []

    role = aws.iam.Role(f"uber-email-{namespace}",
        name=f"uber-email-{namespace}",
        assume_role_policy=_ASSUME_ROLE_POLICY)

    email_policy = aws.iam.Policy(f"uber-email-{namespace}",
        name=f"uber-email-{namespace}",
        path="/",
        description=f"Allow {namespace} to send email via SES",
        policy=_email_policy_document(email_identities))

    aws.iam.RolePolicyAttachment(f"uber-email-{namespace}",
        policy_arn=email_policy.arn,
        role=role.name)

    if lambda_arns:
        lambda_policy = aws.iam.Policy(f"uber-lambda-invoke-{namespace}",
            name=f"uber-lambda-invoke-{namespace}",
            path="/",
            description=f"Allow {namespace} to invoke configured Lambda functions",
            policy=_lambda_policy_document(lambda_arns))

        aws.iam.RolePolicyAttachment(f"uber-lambda-invoke-{namespace}",
            policy_arn=lambda_policy.arn,
            role=role.name)

    aws.eks.PodIdentityAssociation(f"uber_email_{namespace}",
        cluster_name=eks.eks_cluster.name,
        namespace=namespace,
        service_account="ubersystem-email",
        role_arn=role.arn)