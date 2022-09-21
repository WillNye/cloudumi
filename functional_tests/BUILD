load("@rules_python//python:defs.bzl", "py_library")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

INT_DEPS = [
    "//common/config:lib",
    "//common/config/tests:test_files",
    "//common/lib/cognito/tests:test_files",
    "//common/lib",
    "//common/tests:test_files",
    "//util/log:lib",
]

EXT_DEPS = [
    requirement("boto3"),
    requirement("botocore"),
    requirement("flake8"),
    requirement("moto"),
    requirement("pytest"),
    requirement("tornado"),
    requirement("ujson"),
]

filegroup(
    name = "src",
    srcs = glob([
        "**/*py",
    ], exclude=[
        "__init__.py",
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

py_binary(
    name = "bin",
    data = [
        "//configs/development_account:saas_development.yaml",
    ],
    srcs_version = "PY3",
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
    },
    srcs = [
        ":src",
    ],
    main = "run_tests.py",
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)