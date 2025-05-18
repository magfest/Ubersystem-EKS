import json
import pulumi
import pulumi_aws as aws
import eks
import nodegroup

eks_pod_identity_agent = aws.eks.Addon("eks-pod-identity-agent",
    cluster_name=eks.eks_cluster.name,
    addon_name="eks-pod-identity-agent")

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
    }])