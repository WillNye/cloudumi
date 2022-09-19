load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "base_metric.py",
        "default_metrics.py",
        "metrics.py",
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
        "//plugins/metrics/cloudwatch:lib",
        "//plugins/metrics/fluent_bit:lib",
        "//common/config:lib",
        "//common/lib",
    ],
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "py_wheel",
    distribution = "common_plugin_metrics",
    python_tag = "py3",
    version = "$(VERSION)",
    deps = [":lib"],
    tags = ["manual"],
)
