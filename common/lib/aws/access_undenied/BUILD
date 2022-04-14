load("@rules_python//python:defs.bzl", "py_library")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

INT_DEPS = [
]

EXT_DEPS = [
    requirement("aws-error-utils"),
    requirement("boto3"),
    requirement("cachetools"),
    requirement("click"),
    requirement("click-log"),
    requirement("colorlog"),
]

REQUIRES = [
    "aws-error-utils",
    "boto3",
    "cachetools",
    "click",
    "click-log",
    "colorlog",
]

filegroup(
    name = "definitions",
    srcs = glob([
        "access_undenied_aws/definitions/*.json",
    ]),
)

filegroup(
    name = "src_files",
    srcs = glob([
        "**/*.py",
    ]),
)

py_library(
    name = "lib",
    data = [
        ":definitions",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)
