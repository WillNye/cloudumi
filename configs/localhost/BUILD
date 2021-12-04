filegroup(
    name = "configs",
    srcs = glob([
        "*.yaml",
        "saas_saml_cloudumi_com_certs/*.yaml",
        "ssas_auth0_cloudumi_com/*.yaml",
        "ssas_aws_Sso_cloudumi_com/*.yaml",
        "tenant_configurations/*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

exports_files(glob([
    "*.yaml",
]))