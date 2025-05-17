import json
import pulumi
import pulumi_aws as aws
import eks
import vpc

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

nodes = aws.eks.NodeGroup("Ubersystem",
    cluster_name=eks.eks_cluster.name,
    node_group_name="Ubersystem",
    node_role_arn=node_role.arn,
    subnet_ids=[subnet.id for subnet in vpc.private_subnets],
    scaling_config={
        "desired_size": 1,
        "max_size": 2,
        "min_size": 1,
    },
    update_config={
        "max_unavailable": 1,
    },
    instance_types=["t3.medium"])