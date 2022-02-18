load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "test_aws",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_aws.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_change_request",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_change_request.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_generic",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_generic.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_policies",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_policies.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_requests_v2",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_requests_v2.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)
