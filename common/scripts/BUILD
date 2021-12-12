load("@rules_python//python:defs.bzl", "py_binary")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
py_binary(
    name = "initialize_dynamodb",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        "initialize_dynamodb.py"
    ],
    env = {
        # Get this by including it (via data = []) and then searching for it: `find -L . -iname "saas_development.yaml"`
        # Note: `bazel info --show_make_env` will show all available predefined variables
        # "CONFIG_LOCATION": "$(GENDIR)/api/bin.local.runfiles/cloudumi/configs/development_account/saas_development.yaml",
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common/config:lib",
        "//common:lib",
        requirement("botocore"),
        requirement("tenacity"),
        requirement("ujson"),
    ],
    visibility = ["//visibility:public"],
)
