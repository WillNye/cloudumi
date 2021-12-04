load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")
load("@io_bazel_rules_docker//container:container.bzl", "container_image")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src",
    srcs = [
        "__init__.py",
        "__main__.py",
        "routes.py",
    ],
)

filegroup(
    name = "v1",
    srcs = [
        ":src",
        "//api/handlers:v1",
    ]
)

filegroup(
    name = "v2",
    srcs = [
        ":src",
        "//api/handlers:v2",
    ]
)

filegroup(
    name = "v3",
    srcs = [
        ":src",
        "//api/handlers:v3",
    ]
)

py_library(
    name = "bin.v1",
    srcs_version = "PY3",
    srcs = [
        ":v1",
    ],
    data = [
    ],
    deps = [
        "//common/config:lib",
        requirement("email_validator"),
        requirement("uvloop"),
        requirement("marshmallow"),
        requirement("policyuniverse"),
        requirement("newrelic"),
        requirement("tornado"),
        requirement("sentry_sdk"),
        requirement("aiohttp"),
        requirement("ujson"),
    ]
)

py_binary(
    name = "bin.v2",
    srcs_version = "PY3",
    srcs = [
        ":v2",
    ],
    main = "__main__.py",
    data = [
    ],
    deps = [
        "//common/config:lib",
        requirement("email_validator"),
        requirement("uvloop"),
        requirement("marshmallow"),
        requirement("policyuniverse"),
        requirement("newrelic"),
        requirement("tornado"),
        requirement("sentry_sdk"),
        requirement("aiohttp"),
        requirement("ujson"),
    ],
)

py_binary(
    name = "bin.v3",
    srcs_version = "PY3",
    srcs = [
        ":v3",
    ],
    main = "__main__.py",
    data = [
    ],
    deps = [
        "//common/config:lib",
        requirement("email_validator"),
        requirement("uvloop"),
        requirement("marshmallow"),
        requirement("policyuniverse"),
        requirement("newrelic"),
        requirement("tornado"),
        requirement("sentry_sdk"),
        requirement("aiohttp"),
        requirement("ujson"),
    ],
)

py_wheel(
    name = "py_wheel",
    distribution = "cloudumi_api",
    python_tag = "py3",
    version = "0.0.1",
    deps = [":lib"],
    tags = ["manual"],
)