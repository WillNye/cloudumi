load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_library(
    name = "lib",
    srcs = glob([
        "**/*py",
    ]),
    visibility = ["//visibility:public"],
)

py_test(
    name = "test_main",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_main.py",
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
