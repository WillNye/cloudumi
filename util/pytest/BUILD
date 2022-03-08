load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package", "py_wheel")

exports_files([
    "wrapper.py",
    ".pylintrc",
    "conftest.py",
    "fixtures.py",
    "test_configuration.yaml",
])

py_library(
    name = "fixtures",
    srcs_version = "PY3",
    srcs = [
        "__init__.py",
        "conftest.py",
    ],
    deps = [
        # requirement("boto3"),
        # requirement("pytest"),
        # requirement("redislite"),
        # requirement("mock"),
        # requirement("mockredis"),
        # requirement("moto"),
        # requirement("tornado"),
    ],
)

py_package(
    name = "fixtures_pkg",
    packages = ["util.pytest"],
    deps = [":fixtures"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_fixtures",
    python_tag = "py3",
    version = "0.0.1",
    deps = [":fixtures_pkg"],
)