load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

filegroup(
    name = "src_files",
    srcs = glob([
        "**/*.py"
    ]),
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = [
        "//common/lib",
        requirement("pynamodax"),
        requirement("amazon-dax-client"),
    ],
    visibility = ["//visibility:public"],
)