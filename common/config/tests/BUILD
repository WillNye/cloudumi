load("@cloudumi_python_ext//:requirements.bzl", "requirement")

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
    requirement("pytest"),
    requirement("tornado"),
]

py_test(
    name = "test_config",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_config.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)

py_test(
    name = "test_account",
    data = [
        "//configs/development_account:configs",
        "//common/config:weep_config",
    ],
    srcs = [
        "test_account.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)

py_test(
    name = "test_role_access",
    data = [
        "//configs/development_account:configs",
        "//common/config:weep_config",
    ],
    srcs = [
        "test_role_access.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)

py_test(
    name = "test_ip_restrictions",
    data = [
        "//configs/development_account:configs",
        "//common/config:weep_config",
        "//common/tests:test_files",
    ],
    srcs = [
        "test_ip_restrictions.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_cluster_dev",
    },
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)