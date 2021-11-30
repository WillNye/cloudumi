load("@rules_python//python:defs.bzl", "py_library")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "internal_demo_route.py",
    ),
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    deps = [
        "//common/config:lib",
        "//common/handlers:lib",
        "//common/lib",
    ],
    visibility = ["//visibility:public"],
)
