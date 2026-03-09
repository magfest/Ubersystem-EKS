import os
import json
import pulumi
import pulumi_aws as aws
import eks
import nodegroup

eks_pod_identity_agent = aws.eks.Addon("eks-pod-identity-agent",
    cluster_name=eks.eks_cluster.name,
    addon_name="eks-pod-identity-agent",
    opts = pulumi.ResourceOptions(depends_on=[eks.eks_cluster], replace_with=[eks.eks_cluster]))

ebs_role = aws.iam.Role("ebs-csi",
    name = "ebs-csi",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
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

aws.iam.RolePolicyAttachment("ebs_policy",
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy",
    role=ebs_role.name)

ebs_csi_driver = aws.eks.Addon("aws-ebs-csi-driver",
    cluster_name=eks.eks_cluster.name,
    addon_name="aws-ebs-csi-driver",
    pod_identity_associations=[{
        "role_arn": ebs_role.arn,
        "service_account": "ebs-csi-controller-sa"
    }],
    opts = pulumi.ResourceOptions(depends_on=[eks.eks_cluster], replace_with=[eks.eks_cluster]))


vpc_cni_role = aws.iam.Role("vpc_cni",
    name = "vpc_cni",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
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

aws.iam.RolePolicyAttachment("vpc_cni_policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    role=vpc_cni_role.name)

aws.eks.Addon("vpc-cni",
    cluster_name=eks.eks_cluster.name,
    addon_name="vpc-cni",
    pod_identity_associations=[{
        "role_arn": vpc_cni_role.arn,
        "service_account": "aws-node"
    }],
    configuration_values=json.dumps({
        "env": {
        "ENABLE_PREFIX_DELEGATION": "true"
        }
    }),
    opts = pulumi.ResourceOptions(depends_on=[eks.eks_cluster], replace_with=[eks.eks_cluster]))

alb_controller_role = aws.iam.Role("alb-role",
    name = "alb-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
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

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path,"./elb_controller_iam.json"), "r") as file:
    alb_policy_document = file.read()

alb_controller_policy = aws.iam.Policy(
    "aws-load-balancer-controller-policy",
    name="AWSLoadBalancerControllerIAMPolicy",
    policy=alb_policy_document,
)

role_policy_attachment = aws.iam.RolePolicyAttachment(
    "alb-controller-role-attachment",
    role=alb_controller_role.name,
    policy_arn=alb_controller_policy.arn,
)

pod_identity_association = aws.eks.PodIdentityAssociation(
    "alb-controller-pod-identity",
    cluster_name=eks.eks_cluster.name,
    namespace="kube-system",
    service_account="aws-load-balancer-controller",
    role_arn=alb_controller_role.arn,
)