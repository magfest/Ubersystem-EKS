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

# Each (name suffix, subnet ids) pair gets one nodegroup per generation below.
if config.get_object("nodegroup_subnet_ids"):
    subnet_sets = [(f"-{subnet_id}", [subnet_id,]) for subnet_id in config.get_object("nodegroup_subnet_ids")]
else:
    subnet_sets = [("", [subnet.id for subnet in vpc.private_subnets])]

# RAMS:nodegroups lets several generations of nodegroups run side by side, so
# workloads can be drained onto new instances before the old ones are removed.
# Changing instance_types on a nodegroup forces EKS to replace it outright.
#
#   RAMS:nodegroups:
#     - instance_type: t4g.xlarge    # unnamed: the original Ubersystem-* nodegroups
#     - name: v2                     # named: Ubersystem-*-v2 with its own launch template
#       instance_type: t4g.2xlarge
#       nodes: 2                     # optional, defaults to RAMS:nodes
#
# Named generations set the instance type in their launch template instead of
# on the nodegroup, so later instance type changes roll through in place
# (honoring max_unavailable) rather than replacing the nodegroup.
#
# Without RAMS:nodegroups, a single unnamed generation using RAMS:instance_type is created.
generations = config.get_object("nodegroups") or [{}]

for generation in generations:
    name = generation.get("name")
    instance_type = generation.get("instance_type") or config.require("instance_type")
    nodes = generation.get("nodes") or config.require_int("nodes")

    if name:
        generation_template = aws.ec2.LaunchTemplate(f"Ubersystem-{name}",
            instance_type=instance_type,
            vpc_security_group_ids=[eks.node_security_group.id,]
        )
        instance_types = None
    else:
        generation_template = template
        instance_types = [instance_type]

    for subnet_suffix, subnet_ids in subnet_sets:
        nodegroup_name = f"Ubersystem{subnet_suffix}-{name}" if name else f"Ubersystem{subnet_suffix}"
        aws.eks.NodeGroup(nodegroup_name,
            cluster_name=eks.eks_cluster.name,
            node_group_name=nodegroup_name,
            node_role_arn=node_role.arn,
            subnet_ids=subnet_ids,
            scaling_config={
                "desired_size": nodes,
                "max_size": nodes,
                "min_size": 1,
            },
            update_config={
                "max_unavailable": 1,
            },
            instance_types=instance_types,
            launch_template={
                "version": generation_template.latest_version,
                "id": generation_template.id
            },
            ami_type="AL2023_ARM_64_STANDARD"
        )

