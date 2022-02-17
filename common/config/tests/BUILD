load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "tests",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "__init__.py",
        "test_account.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    main = "test_account.py",
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