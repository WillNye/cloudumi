filegroup(
    name = "templates",
    data = glob([
        "templates/*",
    ])
)

py_binary(
    name = "terraform_config_parser",
    data = [":templates"],
    srcs = ["terraform_config_parser.py"],
)