load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

pytest_test(
    name = "test_config",
    srcs = [
        "test_config.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_role_access",
    srcs = [
        "test_role_access.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)

pytest_test(
    name = "test_ip_restrictions",
    srcs = [
        "test_ip_restrictions.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)