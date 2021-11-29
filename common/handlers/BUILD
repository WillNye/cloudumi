load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "base.py",    
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
        "//cloudumi_common/cloudumi_common/exceptions:lib",
        "//cloudumi_common/cloudumi_common/lib",
        requirement("pytz"),
        requirement("redis"),
        requirement("tornado"),
        requirement("ujson"),
        requirement("redis-py-cluster"),
    ],
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "py_wheel",
    distribution = "cloudumi_common_lib",
    python_tag = "py3",
    version = "$(VERSION)",
    deps = [":lib"],
    tags = ["manual"],
)
