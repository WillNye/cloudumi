load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")

exports_files(
    srcs = [
        "initialize_dynamodb.py",
        "initialize_redis.py",
    ],
    visibility = ["//visibility:public"]
)

py_binary(
    name = "initialize_dynamodb",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        "initialize_dynamodb.py",
    ],
    env = {
        # Get this by including it (via data = []) and then searching for it: `find -L . -iname "saas_development.yaml"`
        # Note: `bazel info --show_make_env` will show all available predefined variables
        # "CONFIG_LOCATION": "$(GENDIR)/api/bin.runfiles/cloudumi/configs/development_account/saas_development.yaml",
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common/config:lib",
        "//common:lib",
        "//util/debug",
        requirement("botocore"),
        requirement("tenacity"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "initialize_redis",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        "initialize_redis.py",
    ],
    env = {
        # Get this by including it (via data = []) and then searching for it: `find -L . -iname "saas_development.yaml"`
        # Note: `bazel info --show_make_env` will show all available predefined variables
        # "CONFIG_LOCATION": "$(GENDIR)/api/bin.runfiles/cloudumi/configs/development_account/saas_development.yaml",
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common/celery_tasks:lib",
        "//common/config:lib",
        "//common:lib",
        "//util/debug",
        requirement("botocore"),
        requirement("tenacity"),
    ],
    visibility = ["//visibility:public"],
)