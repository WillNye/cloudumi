load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_library(
    name = "test_files",
    srcs = glob(["test_*.py"]),
    visibility = ["//visibility:public"],
)

pytest_test(
    name = "test_cloud_credential_authorization_mapping",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_cloud_credential_authorization_mapping.py",
    ],
    deps = [
    ],
)
