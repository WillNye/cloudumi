load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "test_aws",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_aws.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_change_request",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_change_request.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_generic",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_generic.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_policies",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_policies.py",
    ],
    env = {
       "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_requests_v2",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_requests_v2.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)
