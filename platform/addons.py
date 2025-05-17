import json
import pulumi
import pulumi_aws as aws
import eks
import nodegroup

eks_pod_identity_agent = aws.eks.Addon("eks-pod-identity-agent",
    cluster_name=eks.eks_cluster.name,
    addon_name="eks-pod-identity-agent")