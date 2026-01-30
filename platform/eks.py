import pulumi
import json
import pulumi_aws as aws
import vpc

config = pulumi.Config()

cluster_role = aws.iam.Role("cluster",
    name="eks-cluster",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": [
                "sts:AssumeRole",
                "sts:TagSession",
            ],
            "Effect": "Allow",
            "Principal": {
                "Service": "eks.amazonaws.com",
            },
        }],
    }))

cluster_amazon_eks_cluster_policy = aws.iam.RolePolicyAttachment("cluster_AmazonEKSClusterPolicy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    role=cluster_role.name)

node_security_group = aws.ec2.SecurityGroup("allow_internet",
    vpc_id=vpc.vpc_id,
    egress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "cidr_blocks": ["0.0.0.0/0"],
    }],
    ingress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "self": True
    },
    {
        "from_port": 32000,
        "to_port": 32000,
        "protocol": "TCP",
        "cidr_blocks": [subnet.cidr_block for subnet in vpc.public_subnets]
    },
    {
        "from_port": 32001,
        "to_port": 32001,
        "protocol": "TCP",
        "cidr_blocks": [subnet.cidr_block for subnet in vpc.public_subnets]
    }]
)

eks_cluster = aws.eks.Cluster("Ubersystem",
    name=config.require("cluster_name"),
    access_config={
        "authentication_mode": "API",
    },
    role_arn=cluster_role.arn,
    version=config.require("kubernetes_version"),
    vpc_config={
        "subnet_ids": [subnet.id for subnet in vpc.private_subnets],
        "endpoint_private_access": True,
        "endpoint_public_access": True,
        "security_group_ids": [node_security_group.id]
    },
    opts = pulumi.ResourceOptions(depends_on=[cluster_amazon_eks_cluster_policy]))

for cluster_admin in config.require_object("cluster_admins"):
    aws.eks.AccessEntry(
        resource_name=f"{cluster_admin}",
        cluster_name=eks_cluster.name,
        principal_arn=cluster_admin)
    aws.eks.AccessPolicyAssociation(cluster_admin,
        cluster_name=eks_cluster.name,
        policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
        principal_arn=cluster_admin,
        access_scope={
            "type": "cluster",
        })