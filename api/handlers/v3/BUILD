load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")
load("@io_bazel_rules_docker//container:container.bzl", "container_image")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src",
    srcs = glob([
        "*.py",
    ]),
)

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src",
        "//api/handlers/v3/api_keys:src",
        "//api/handlers/v3/auth:src",
        "//api/handlers/v3/auth/sso:src",
        "//api/handlers/v3/config:src",
        "//api/handlers/v3/downloads:src",
        "//api/handlers/v3/identity:src",
        "//api/handlers/v3/integrations:src",
        "//api/handlers/v3/services:src",
        "//api/handlers/v3/services/aws:src",
        "//api/handlers/v3/slack:src",
        "//api/handlers/v3/tasks:src",
        "//api/handlers/v3/tenant_registration:src",
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
    visibility = ["//visibility:public"],
)
