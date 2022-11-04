load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

DEPS = [
    "//common/lib",
    requirement("asgiref"),
    requirement("boto3"),
    requirement("botocore"),
    requirement("logmatic-python"),
    requirement("pytz"),
    requirement("ruamel.yaml"),
    requirement("sentry_sdk"),
    requirement("ujson"),
]

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "config.py",
        "ip_restrictions.py",
        "logger.py",
        "models.py",
        "role_access.py",
    ),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "noq_config",
    data = [
        "noq.yaml",
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    data = [
        ":noq_config",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = DEPS,
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
