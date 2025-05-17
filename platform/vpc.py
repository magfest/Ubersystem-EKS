import pulumi
import pulumi_aws as aws

import ipaddress

config = pulumi.Config()

vpc = aws.ec2.Vpc(
    "Uber_EKS",
    cidr_block=config.require("cidr_block"),
    assign_generated_ipv6_cidr_block=True,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": "Uber_EKS"
    })

# Create an Internet Gateway
internet_gateway = aws.ec2.InternetGateway("internet-gateway", vpc_id=vpc.id)

# Create a route table for the public subnet
public_route_table = aws.ec2.RouteTable("public-route-table", vpc_id=vpc.id)
private_route_table = aws.ec2.RouteTable("private-route-table", vpc_id=vpc.id)

# Create a route to the internet gateway
aws.ec2.Route("public-internet-route", route_table_id=public_route_table.id, destination_cidr_block="0.0.0.0/0", gateway_id=internet_gateway.id)

cidr = ipaddress.IPv4Network(config.require("cidr_block"))
subnets = cidr.subnets(prefixlen_diff=8)
private_subnets = []
public_subnets = []
for az in config.require_object("availability_zones"):
    private_subnet = aws.ec2.Subnet(
        f"private-{az}",
        vpc_id=vpc.id,
        cidr_block=str(next(subnets)),
        availability_zone=az,
        tags={
            "Name": f"uber-private-{az}"
        })
    private_subnet_route_table_association = aws.ec2.RouteTableAssociation(f"private-{az}", subnet_id=private_subnet.id, route_table_id=private_route_table.id)
    private_subnets.append(private_subnet)
    
    public_subnet = aws.ec2.Subnet(
        f"public-{az}",
        vpc_id=vpc.id,
        cidr_block=str(next(subnets)),
        availability_zone=az,
        tags={
            "Name": f"uber-public-{az}"
        })
    public_subnet_route_table_association = aws.ec2.RouteTableAssociation(f"public-{az}", subnet_id=public_subnet.id, route_table_id=public_route_table.id)
    public_subnets.append(public_subnet)

endpoint_sg = aws.ec2.SecurityGroup("allow_endpoint_access",
    vpc_id=vpc.id,
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
    }
)

aws.ec2.Route("private-internet-route", route_table_id=private_route_table.id, destination_cidr_block="0.0.0.0/0", nat_gateway_id=nat.id)
