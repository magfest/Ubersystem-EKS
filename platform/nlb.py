import pulumi
import pulumi_aws as aws
import vpc
import cert

security_group = aws.ec2.SecurityGroup("allow_incoming",
    vpc_id=vpc.vpc.id,
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
        "cidr_blocks": ["0.0.0.0/0"]
    }]
)

loadbalancer = aws.lb.LoadBalancer("loadbalancer",
    name="Uber",
    internal=False,
    load_balancer_type="application",
    subnets=[subnet.id for subnet in vpc.public_subnets],
    security_groups=[security_group.id])

target_group = aws.lb.TargetGroup("target",
    vpc_id=vpc.vpc.id,
    name="Uber",
    port=32000,
    protocol="HTTP"
)

listener = aws.lb.Listener("listener",
    load_balancer_arn=loadbalancer.arn,
    port=443,
    protocol="HTTPS",
    ssl_policy="ELBSecurityPolicy-2016-08",
    certificate_arn=cert.validation.certificate_arn,
    default_actions=[{
        "type": "forward",
        "target_group_arn": target_group.arn,
    }])