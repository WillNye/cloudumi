load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_library(
    name = "test_files",
    srcs = glob(["test_*.py"]),
    visibility = ["//visibility:public"],
)

pytest_test(
    name = "test_aws",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_aws.py",
        "test_change_request.py",
        "test_generic.py",
        "test_policies.py",
        "test_requests_v2.py",
    ],
    deps = [
    ],
)
