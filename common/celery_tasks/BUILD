load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "celery_tasks.py",
        "run.py",
    ),
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = [
        requirement("celery"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.local",
    data = [
        "//cloudumi_config/configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
        "CONFIG_LOCATION": "cloudumi_config/configs/development_account:saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        requirement("celery"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.s3",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
        "CONFIG_LOCATION": "s3://noq-tenant-configuration.node.dev1.259868150464.us-west-2/tenant_configurations/saas_development.yaml",
        "AWS_PROFILE": "noq_dev"
    },
    deps = [
        requirement("celery"),
    ],
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "py_wheel",
    distribution = "cloudumi_common_lib",
    python_tag = "py3",
    version = "$(VERSION)",
    deps = [":lib"],
    tags = ["manual"],
)
