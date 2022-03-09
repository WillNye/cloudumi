load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
# load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package", "py_wheel")

exports_files([
    "wrapper.py",
    ".pylintrc",
    "test_configuration.yaml",
])

py_library(
    name = "fixtures",
    srcs_version = "PY3",
    srcs = [
        "__init__.py",
        "//util/pytest/fixtures:conftest.py",
        "//util/pytest/fixtures:globals.py",
    ],
    deps = [
        "//common:lib",
        "//common/config:lib",
        # "//common/tests:lib",
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
    packages = [
        "common.celery_tasks.celery_tasks",
        "common.config",
        "common.exceptions",
        "common.lib",
        "plugins.celery_tasks",
        "util.pytest",
    ],
    deps = [":fixtures"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_fixtures",
    python_tag = "py3",
    entry_points = {"pytest11": ["fixtures = fixtures.conftest"]},
    strip_path_prefixes = ["util/pytest"],
    version = "0.0.1",
    deps = [":fixtures_pkg"],
)