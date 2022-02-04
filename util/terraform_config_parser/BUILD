load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "templates",
    data = glob([
        "templates/*",
    ])
)

py_binary(
    name = "terraform_config_parser",
    deps = [
        requirement("boto3"),
        requirement("jinja2"),
    ],
    data = [":templates"],
    srcs = ["terraform_config_parser.py"],
)