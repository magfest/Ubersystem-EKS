import pulumi
import pulumi_aws as aws

config = pulumi.Config()
certificate = aws.acm.Certificate("wildcard",
    domain_name=config.require("wildcard_domain"),
    validation_method="DNS")

zone = aws.route53.get_zone(name=config.require("wildcard_domain").replace("*.", ""),
    private_zone=False)

records = []
def generate_records(validation_records):
    for idx, dvo in enumerate(validation_records):
        records.append(aws.route53.Record(f"record-{idx}",
            allow_overwrite=True,
            name=dvo.resource_record_name,
            records=[dvo.resource_record_value,],
            type=aws.route53.RecordType(dvo.resource_record_type),
            ttl=60,
            zone_id=zone.id
        ))


validation = aws.acm.CertificateValidation("validation",
    certificate_arn=certificate.arn,
    validation_record_fqdns=[record.fqdn for record in records])

certificate.domain_validation_options.apply(generate_records)
