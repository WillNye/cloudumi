load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "test_accessui",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_accessui.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("pytest"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_base",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_base.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("pytest"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_policies_handlers",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_policies_handlers.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("pytest"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_role_login_api",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_role_login_api.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)

py_test(
    name = "test_users",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_users.py",
    ],
    env = {
        "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
    },
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//common/tests:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        "//util/tests/fixtures:lib",
        requirement("asgiref"),
        requirement("pytest"),
        requirement("tornado"),
    ],
)
