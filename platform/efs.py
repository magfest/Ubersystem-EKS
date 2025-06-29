import json
import pulumi
import pulumi_aws as aws
import eks
import vpc
import nodegroup

config = pulumi.Config()

efs_sg = aws.ec2.SecurityGroup("allow_efs_access",
    vpc_id=vpc.vpc_id,
    egress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "cidr_blocks": ["0.0.0.0/0"],
    }],
    ingress=[{
        "from_port": 2049,
        "to_port": 2049,
        "protocol": "TCP",
        "cidr_blocks": [subnet.cidr_block for subnet in vpc.private_subnets]
    }])

efs_role = aws.iam.Role("efs-csi",
    name = "efs-csi",
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

aws.iam.RolePolicyAttachment("efs_policy",
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy",
    role=efs_role.name)

efs_csi_driver = aws.eks.Addon("aws-efs-csi-driver",
    cluster_name=eks.eks_cluster.name,
    addon_name="aws-efs-csi-driver",
    pod_identity_associations=[{
        "role_arn": efs_role.arn,
        "service_account": "efs-csi-controller-sa"
    }],
    opts = pulumi.ResourceOptions(depends_on=[eks.eks_cluster]))

efs = aws.efs.FileSystem("Ubersystem",
    tags={
        "Name": config.require("cluster_name"),
    })

for idx, subnet in enumerate(vpc.private_subnets):
    aws.efs.MountTarget(f"target-{config.require_object('availability_zones')[idx]}",
        file_system_id=efs.id,
        subnet_id=subnet.id,
        security_groups=[efs_sg.id,])