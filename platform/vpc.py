import pulumi
import pulumi_aws as aws

import ipaddress

config = pulumi.Config()

vpc_id = config.get("vpc_id")
if not vpc_id:
    vpc_id = aws.ec2.Vpc(
        "Uber_EKS",
        cidr_block=config.require("cidr_block"),
        assign_generated_ipv6_cidr_block=True,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={
            "Name": "Uber_EKS"
        }).id

# Create an Internet Gateway
if not config.get("skip_internet_gateway"):
    internet_gateway = aws.ec2.InternetGateway("internet-gateway", vpc_id=vpc_id)

    # Create a route table for the public subnet
    public_route_table = aws.ec2.RouteTable("public-route-table", vpc_id=vpc_id)
    private_route_table = aws.ec2.RouteTable("private-route-table", vpc_id=vpc_id)

    # Create a route to the internet gateway
    aws.ec2.Route("public-internet-route", route_table_id=public_route_table.id, destination_cidr_block="0.0.0.0/0", gateway_id=internet_gateway.id)

cidr = ipaddress.IPv4Network(config.require("cidr_block"))
subnets = cidr.subnets(prefixlen_diff=config.require_int("subnet_prefixlen"))
for i in range(config.require_int("subnet_cidr_block")):
    next(subnets)
private_subnets = []
public_subnets = []
if config.get_object("private_subnet_ids"):
    for subnet_id in config.get_object("private_subnet_ids"):
        private_subnets.append(aws.ec2.get_subnet(id=subnet_id))
else:
    for az in config.require_object("availability_zones"):
        private_subnet = aws.ec2.Subnet(
            f"private-{az}",
            vpc_id=vpc_id,
            cidr_block=str(next(subnets)),
            availability_zone=az,
            tags={
                "Name": f"uber-private-{az}"
            })
        private_subnet_route_table_association = aws.ec2.RouteTableAssociation(f"private-{az}", subnet_id=private_subnet.id, route_table_id=private_route_table.id)
        private_subnets.append(private_subnet)
    
if config.get_object("public_subnet_ids"):
    for subnet_id in config.get_object("public_subnet_ids"):
        public_subnets.append(aws.ec2.get_subnet(id=subnet_id))
else:
    for az in config.require_object("availability_zones"):
        public_subnet = aws.ec2.Subnet(
            f"public-{az}",
            vpc_id=vpc_id,
            cidr_block=str(next(subnets)),
            availability_zone=az,
            tags={
                "Name": f"uber-public-{az}"
            })
        public_subnet_route_table_association = aws.ec2.RouteTableAssociation(f"public-{az}", subnet_id=public_subnet.id, route_table_id=public_route_table.id)
        public_subnets.append(public_subnet)

if not config.get("skip_nat_gateway"):
    endpoint_sg = aws.ec2.SecurityGroup("allow_endpoint_access",
        vpc_id=vpc_id,
        egress=[{
            "from_port": 0,
            "to_port": 0,
            "protocol": "-1",
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        ingress=[{
            "from_port": 443,
            "to_port": 443,
            "protocol": "TCP",
            "cidr_blocks": ["0.0.0.0/0"]
        }])

    eip = aws.ec2.Eip("nat_eip",
        domain="vpc")

    nat = aws.ec2.NatGateway("nat",
        subnet_id=public_subnets[0].id,
        allocation_id=eip.id,
        tags={
            "Name": "Ubersystem Internet NAT"
        },
        opts=pulumi.ResourceOptions(delete_before_replace=True)
    )

    aws.ec2.Route("private-internet-route", route_table_id=private_route_table.id, destination_cidr_block="0.0.0.0/0", nat_gateway_id=nat.id)
