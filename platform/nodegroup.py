import json
import pulumi
import base64
from pulumi import Output
import pulumi_aws as aws
import eks
import vpc

config = pulumi.Config()

node_role = aws.iam.Role("node",
    name="eks-node",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": [
                "sts:AssumeRole",
                "sts:TagSession",
            ],
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com",
            },
        }],
    }))

aws.iam.RolePolicyAttachment("worker_policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    role=node_role.name)

aws.iam.RolePolicyAttachment("registry_policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly",
    role=node_role.name)

aws.iam.RolePolicyAttachment("cni_policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    role=node_role.name)

template = aws.ec2.LaunchTemplate("Ubersystem",
    vpc_security_group_ids=[eks.node_security_group.id,]
)

#aws.eks.NodeGroup("Ubersystem",
#    cluster_name=eks.eks_cluster.name,
#    node_group_name="Ubersystem",
#    node_role_arn=node_role.arn,
#    subnet_ids=[subnet.id for subnet in vpc.private_subnets],
#    scaling_config={
#        "desired_size": config.require_int("nodes"),
#        "max_size": config.require_int("nodes"),
#        "min_size": 1,
#    },
#    update_config={
#        "max_unavailable": 1,
#    },
#    instance_types=["t3.medium"],
#    launch_template={
#        "version": template.latest_version,
#        "id": template.id
#    }
#)

aws.eks.NodeGroup("UbersystemArm",
    cluster_name=eks.eks_cluster.name,
    node_group_name="UbersystemArm",
    node_role_arn=node_role.arn,
    subnet_ids=[subnet.id for subnet in vpc.private_subnets],
    scaling_config={
        "desired_size": config.require_int("nodes"),
        "max_size": config.require_int("nodes"),
        "min_size": 1,
    },
    update_config={
        "max_unavailable": 1,
    },
    instance_types=[config.require("instance_type")],
    launch_template={
        "version": template.latest_version,
        "id": template.id
    },
    ami_type="AL2023_ARM_64_STANDARD"
)

