import json
import pulumi
import pulumi_aws as aws

import vpc
import cert
config = pulumi.Config()

nginx_tg = aws.lb.TargetGroup("nginx-internal-tg",
    name="Ubersystem-http",
    port=80,
    protocol="TCP",
    vpc_id=vpc.vpc_id,
    target_type="ip", 
)

nginx_nlb = aws.lb.LoadBalancer("nginx-internal-nlb",
    name="Ubersystem",
    internal=True,
    load_balancer_type="network",
    subnets=[x.id for x in vpc.private_subnets],
    enable_cross_zone_load_balancing=True,
)

nginx_listener = aws.lb.Listener("nginx-listener",
    load_balancer_arn=nginx_nlb.arn,
    port=80,
    protocol="TCP",
    default_actions=[{
        "type": "forward",
        "target_group_arn": nginx_tg.arn
    }]
)

vpc_origin = aws.cloudfront.VpcOrigin("nginx-vpc-origin",
    vpc_origin_endpoint_config={
        "name": "Ubersystem",
        "arn": nginx_nlb.arn,
        "http_port": 80,
        "https_port": 443,
        "origin_protocol_policy": "http-only",
        "origin_ssl_protocols": {
            "items": ["TLSv1.2"],
            "quantity": 1,
        },
    }
)

s3_distribution = aws.cloudfront.Distribution("s3_distribution",
    origins=[{
        "domain_name": nginx_nlb.dns_name,
        "origin_id": config.require("cluster_name"),
        "vpc_origin_config": {
            "vpc_origin_id": vpc_origin.id, 
        }
    }],
    enabled=True,
    is_ipv6_enabled=True,
    default_cache_behavior={
        "allowed_methods": ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
        "cached_methods": ["GET", "HEAD", "OPTIONS"],
        "target_origin_id": config.require("cluster_name"),
        "viewer_protocol_policy": "redirect-to-https",
        "min_ttl": 0,
        "default_ttl": 900,
        "max_ttl": 3600,
        "forwarded_values": {
            "query_string": True,
            "headers": ["*"],
            "cookies": {
                "forward": "all"
            }
        }
    },
    ordered_cache_behaviors=[
        {
            "path_pattern": "/static*",
            "allowed_methods": ["GET", "HEAD", "OPTIONS"],
            "cached_methods": ["GET", "HEAD", "OPTIONS"],
            "target_origin_id": config.require("cluster_name"),
            "min_ttl": 0,
            "default_ttl": 900,
            "max_ttl": 3600,
            "compress": True,
            "viewer_protocol_policy": "redirect-to-https",
            "forwarded_values": {
                "query_string": False,
                "headers": ["Host"],
                "cookies": {
                    "forward": "none"
                }
            }
        }
    ],
    price_class="PriceClass_100",
    viewer_certificate={
        "acm_certificate_arn": cert.certificate_arn,
        "ssl_support_method": "sni-only",
    },
    restrictions={
        "geo_restriction": {
            "restriction_type": "none",
            "locations": []
        }
    },
    aliases=[config.require("wildcard_domain"), *(config.get_object("subject_alternative_names") or [])]
)
