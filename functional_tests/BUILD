load("@rules_python//python:defs.bzl", "py_library")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

INT_DEPS = [
    "//common/config/tests:test_files",
    "//common/lib/cognito/tests:test_files",
    "//common/lib",
    "//common/tests:test_files",
    "//util/log:lib",
]

EXT_DEPS = [
    requirement("boto3"),
    requirement("botocore"),
    requirement("pytest"),
    requirement("tornado"),
    requirement("ujson"),
]

filegroup(
    name = "src",
    srcs = glob([
        "**/*py",
    ]),
)

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)
