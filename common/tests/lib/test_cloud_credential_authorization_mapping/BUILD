load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_test(
    name = "test_cloud_credential_authorization_mapping",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_cloud_credential_authorization_mapping.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)
