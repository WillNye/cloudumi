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
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_change_request",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_change_request.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_generic",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_generic.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_policies",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_policies.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_requests_v2",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_requests_v2.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)
