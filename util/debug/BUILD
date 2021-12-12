load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
    ),
    visibility = ["//visibility:public"],
)

py_library(
    name = "debug",  # can be pulled in like this: //util/debug
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = [
    ],
    visibility = ["//visibility:public"],
)

