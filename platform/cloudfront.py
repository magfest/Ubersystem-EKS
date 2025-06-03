import json
import pulumi
import pulumi_aws as aws

import cert
config = pulumi.Config()

s3_distribution = aws.cloudfront.Distribution("s3_distribution",
    origins=[{
        "domain_name": config.require("base_domain"),
        "origin_id": "Ubersystem",
         "custom_origin_config": {
            "http_port": 80,
            "https_port": 443,
            "origin_protocol_policy": "http-only",
            "origin_ssl_protocols": ["TLSv1.2"],
        },
    }],
    enabled=True,
    is_ipv6_enabled=True,
    default_cache_behavior={
        "allowed_methods": ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
        "cached_methods": ["GET", "HEAD", "OPTIONS"],
        "target_origin_id": "Ubersystem",
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
            "target_origin_id": "Ubersystem",
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
        "acm_certificate_arn": cert.certificate.arn,
        "ssl_support_method": "sni-only",
    },
    restrictions={
        "geo_restriction": {
            "restriction_type": "none",
            "locations": []
        }
    },
    aliases=[config.require("wildcard_domain")]
)