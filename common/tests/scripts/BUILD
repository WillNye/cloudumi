load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_library(
    name = "test_files",
    srcs = glob(["test_*.py"]),
    visibility = ["//visibility:public"],
)

pytest_test(
    name = "test_scripts",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_update_tenants.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)