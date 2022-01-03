filegroup(
    name = "staging",
    data = glob([
        "*.tfvars",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "plan",
    srcs = [
        ":staging",
        "//deploy/terraform/modules/services/dynamo",
        "//deploy/terraform/modules/services/saas_central_account",
        "//deploy/terraform/modules/services/tenant_central_account",
    ],
    outs = [
        "running"
    ],
    executable = True,
    cmd = "terraform plan",
)