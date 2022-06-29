load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package", "py_wheel")

exports_files([
    "wrapper.py",
    "test_configuration.yaml",
])

TEST_INT_DEPS = [
    "//api:lib",
    "//common:lib",
    "//common/celery_tasks:lib",
    "//common/config:lib",
    "//common/exceptions:lib",
    "//identity:lib",
    "//plugins/metrics:lib",
    "//util/tests/fixtures:lib",
]

TEST_EXT_DEPS = [
    requirement("asgiref"),
    requirement("atlassian-python-api"),
    requirement("mock"),
    requirement("moto"),
    requirement("pytest"),
    requirement("pytest_mock"),
    requirement("tornado"),
]

py_library(
    name = "test_dependencies_lib",
    srcs = TEST_EXT_DEPS + TEST_INT_DEPS,
    visibility = ["//visibility:public"],
)

filegroup(
    name = "configs",
    srcs = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

py_library(
    name = "fixtures",
    srcs_version = "PY3",
    srcs = [
        "__init__.py",
        "//util/tests/fixtures:fixtures.py",
        "//util/tests/fixtures:globals.py",
    ],
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        # "//common/tests:lib",
        # requirement("boto3"),
        requirement("fakeredis"),
        requirement("pytest"),
        requirement("pytest_mock"),
        # requirement("mock"),
        # requirement("mockredis"),
        # requirement("moto"),
        # requirement("tornado"),
    ],
)

py_package(
    name = "fixtures_pkg",
    packages = [
        "common",
        "identity",
        "plugins",
        "util",
    ],
    deps = [":fixtures"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_fixtures",
    python_tag = "py3",
    entry_points = {"pytest11": ["fixtures = fixtures.fixtures"]},
    strip_path_prefixes = ["util/tests"],
    version = "0.0.1",
    deps = [":fixtures_pkg"],
)