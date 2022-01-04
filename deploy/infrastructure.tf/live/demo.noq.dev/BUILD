filegroup(
    name = "demo.noq.dev",
    data = glob([
        "*.tfvars",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "staging",
    srcs = [
        "demo.noq.dev",
    ],
    outs = ["terraform_apply_staging"],
    cmd  = "echo 'terraform apply --var-file=demo.noq.dev-staging.tfvars' &>$@"
    executable = True,
    message = "This applies terraform staging configuration",
)

genrule(
    name = "prod",
    srcs = [
        "demo.noq.dev",
    ],
    outs = ["terraform_apply_staging"],
    cmd  = "echo 'terraform apply --var-file=demo.noq.dev-prod.tfvars' &>$@"
    executable = True,
    message = "This applies terraform production configuration",
)