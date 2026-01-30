import pulumi
import pulumi_aws as aws

config = pulumi.Config()    

main_domain = config.require("wildcard_domain")
san_list = config.get_object("subject_alternative_names") or []

certificate_arn = config.get("certificate_arn")
if not certificate_arn:
    certificate = aws.acm.Certificate("ubersystem",
        domain_name=main_domain,
        subject_alternative_names=san_list,
        validation_method="DNS"
    )

    validation_records = []

    all_domains = list(set([main_domain] + san_list))
    all_domains.sort()

    for i, domain in enumerate(all_domains):
        zone = aws.route53.get_zone(
            name=domain.replace("*.", ""), 
            private_zone=False
        )
        
        def get_domain_validation_option(args):
            dvos, domain_name = args
            for dvo in dvos:
                if dvo['domain_name'] == domain_name:
                    return dvo
            return dvos[0]

        validation_option = pulumi.Output.all(certificate.domain_validation_options, domain).apply(get_domain_validation_option)

        record = aws.route53.Record(f"validation-record-{i}",
            allow_overwrite=True,
            name=validation_option['resource_record_name'],
            records=[validation_option['resource_record_value']],
            type=validation_option['resource_record_type'],
            zone_id=zone.id,
            ttl=60
        )
        
        validation_records.append(record.fqdn)

    aws.acm.CertificateValidation("cert-validation",
        certificate_arn=certificate.arn,
        validation_record_fqdns=validation_records
    )

    certificate_arn = certificate.arn