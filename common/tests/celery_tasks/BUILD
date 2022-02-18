load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "test_celery",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_celery.py",
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
