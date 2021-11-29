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
        "//cloudumi_common/cloudumi_common/config:lib",
        "//cloudumi_common/cloudumi_common/handlers:lib",
        "//cloudumi_common/cloudumi_common/lib",
    ],
    visibility = ["//visibility:public"],
)
