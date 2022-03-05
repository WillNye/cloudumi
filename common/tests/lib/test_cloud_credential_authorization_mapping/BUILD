load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_test(
    name = "test_cloud_credential_authorization_mapping",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_cloud_credential_authorization_mapping.py",
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
