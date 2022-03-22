load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

py_library(
    name = "lib",
    srcs = glob([
        "**/*py",
    ]),
    visibility = ["//visibility:public"],
)

pytest_test(
    name = "test_main",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_main.py",
    ],
    deps = [
        "//util/tests:test_dependencies_lib",
    ],
)
