load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")
load("@io_bazel_rules_docker//container:container.bzl", "container_image")
load("@nexus_python_ext//:requirements.bzl", "requirement")

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
        "//cloudumi_api/cloudumi_api/handlers:v1",
    ]
)

filegroup(
    name = "v2",
    srcs = [
        ":src",
        "//cloudumi_api/cloudumi_api/handlers:v2",
    ]
)

filegroup(
    name = "v3",
    srcs = [
        ":src",
        "//cloudumi_api/cloudumi_api/handlers:v3",
    ]
)

py_library(
    name = "lib.v1",
    srcs_version = "PY3",
    srcs = [
        ":v1",
    ],
    data = [
    ],
    deps = [
        requirement("email_validator"),
        requirement("uvloop"),
        requirement("marshmallow"),
        requirement("policyuniverse"),
    ]
)

py_binary(
    name = "bin.v1",
    srcs_version = "PY3",
    srcs = [
        ":v1",
    ],
    main = "__main__.py",
    data = [
    ],
    deps = [
        requirement("email_validator"),
        requirement("uvloop"),
        requirement("marshmallow"),
        requirement("policyuniverse"),
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