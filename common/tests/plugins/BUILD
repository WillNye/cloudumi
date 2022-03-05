load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "test_auth",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_auth.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
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
    name = "test_celery_tasks",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_celery_tasks.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
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
