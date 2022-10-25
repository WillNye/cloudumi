load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_library(
    name = "test_files",
    srcs = glob(["test_*.py"]),
    visibility = ["//visibility:public"],
)

pytest_test(
    name = "tests",
    srcs = [
        "test_config.py",
        "test_ip_restrictions.py",
        "test_models.py",
        "test_role_access.py",
    ],
    deps = [
    ],
)
