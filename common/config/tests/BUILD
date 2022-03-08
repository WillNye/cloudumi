load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/pytest:defs.bzl", "pytest_test")

INT_DEPS = [
    "//common:lib",
    "//common/config:lib",
    "//common/exceptions:lib",
    "//common/tests:lib",
    "//identity:lib",
    "//plugins/metrics:lib",
]

EXT_DEPS = [
    requirement("asgiref"),
    requirement("tornado"),
]

pytest_test(
    name = "test_config",
    srcs = [
        "test_config.py",
    ],
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)

pytest_test(
    name = "test_account",
    srcs = [
        "test_account.py",
    ],
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)

pytest_test(
    name = "test_role_access",
    srcs = [
        "test_role_access.py",
    ],
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)

pytest_test(
    name = "test_ip_restrictions",
    srcs = [
        "test_ip_restrictions.py",
    ],
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)