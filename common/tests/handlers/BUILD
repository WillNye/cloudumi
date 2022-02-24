load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "test_accessui",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_accessui.py",
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
    name = "test_base",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_base.py",
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
    name = "test_role_login_api",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_role_login_api.py",
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
    name = "test_users",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_users.py",
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
