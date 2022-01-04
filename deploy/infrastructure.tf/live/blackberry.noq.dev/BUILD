filegroup(
    name = "blackberry.noq.dev",
    data = glob([
        "*.tfvars",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "staging",
    srcs = [
        "blackberry.noq.dev",
    ],
    outs = ["terraform_apply_staging"],
    cmd  = "echo 'terraform apply --var-file=blackberry.noq.dev-staging.tfvars' &>$@"
    executable = True,
    message = "This applies terraform staging configuration",
)

genrule(
    name = "prod",
    srcs = [
        "blackberry.noq.dev",
    ],
    outs = ["terraform_apply_staging"],
    cmd  = "echo 'terraform apply --var-file=blackberry.noq.dev-prod.tfvars' &>$@"
    executable = True,
    message = "This applies terraform production configuration",
)