load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src_files",
    srcs = glob([
        "**/*.py"
    ]),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "data_files",
    srcs = glob([
        "**/*.json"
    ]),
    visibility = ["//visibility:public"],
)


py_library(
    name = "lib",
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    data = [
        ":data_files",
    ],
    deps = [
        "//common/lib",
        "//common/templates:lib",
        requirement("noq-dax-client"),
        requirement("pynamodax"),
    ],
    visibility = ["//visibility:public"],
)