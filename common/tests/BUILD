load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "test_files",
    data = ["conftest.py"],
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    srcs = [
        "conftest.py",
        "globals.py",
        "util.py",
    ],
    visibility = ["//visibility:public"],
)

py_test(
    name = "test_main",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "test_main.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_cluster_dev",
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
