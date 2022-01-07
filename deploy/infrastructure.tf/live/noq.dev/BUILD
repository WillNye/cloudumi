filegroup(
    name = "noq.dev",
    data = glob([
        "*.tfvars",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "staging",
    srcs = [
        "noq.dev",
    ],
    outs = ["terraform_apply_staging"],
    cmd  = "echo 'terraform apply --var-file=noq.dev-staging.tfvars' &>$@",
    executable = True,
    message = "This applies terraform staging configuration",
)

genrule(
    name = "prod",
    srcs = [
        "noq.dev",
    ],
    outs = ["terraform_apply_prod"],
    cmd  = "echo 'terraform apply --var-file=noq.dev-prod.tfvars' &>$@",
    executable = True,
    message = "This applies terraform production configuration",
)