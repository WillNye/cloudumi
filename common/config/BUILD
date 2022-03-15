load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "account.py",
        "config.py",
        "ip_restrictions.py",
        "models.py",
        "role_access.py",
    ),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "weep_config",
    data = [
        "weep.yaml",
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    data = [
        ":weep_config",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = [
        "//common/lib",
        requirement("boto3"),
        requirement("botocore"),
        requirement("logmatic-python"),
        requirement("sentry_sdk"),
        requirement("ujson"),
        requirement("asgiref"),
        requirement("pytz"),
        requirement("ruamel.yaml"),
    ],
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "py_wheel",
    distribution = "common_lib",
    python_tag = "py3",
    version = "$(VERSION)",
    deps = [":lib"],
    tags = ["manual"],
)
