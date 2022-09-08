load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@io_bazel_rules_docker//container:container.bzl", "container_image")
load("@io_bazel_rules_docker//python:image.bzl", "py_layer")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src",
    srcs = [
        "__init__.py",
        "__main__.py",
        "routes.py",
    ]
)

# filegroup(
#     name = "web_site_sources",
#     srcs = glob([
#         "templates/**/*",
#     ])
# )

filegroup(
    name = "docs_sources",
    srcs = glob([
        "docs/**/*",
    ]),
    visibility = ["//visibility:public"],
)

INT_DEPS = [
    "//api/handlers:lib",
    "//common/celery_tasks:lib",
    "//common/config:lib",
    "//common/handlers:lib",
    "//functional_tests:lib",
    "//identity:lib",
    "//plugins:lib",
    "//plugins/auth:lib",
    "//plugins/celery_tasks:lib",
    "//plugins/config:lib",
    "//plugins/group_mapping:lib",
    "//plugins/metrics:lib",
    "//plugins/policies:lib",
    "//util/log:lib",
]

EXT_DEPS = [
    requirement("aiohttp"),
    requirement("aiozipkin"),
    requirement("atlassian-python-api"),
    requirement("bcrypt"),
    requirement("cloudaux"),
    requirement("cryptography"),
    requirement("debugpy"),
    requirement("deepdiff"),
    requirement("ed25519"),
    requirement("email_validator"),
    requirement("furl"),
    requirement("gitpython"),
    requirement("jsonschema"),
    requirement("marshmallow"),
    requirement("okta"),
    requirement("okta-jwt"),
    requirement("pandas"),
    requirement("parliament"),
    requirement("password_strength"),
    requirement("policy_sentry"),
    requirement("policyuniverse"),
    requirement("ptvsd"),
    requirement("pyjwt"),
    requirement("pytest"),
    requirement("requests"),
    requirement("retrying"),
    requirement("sentry_sdk"),
    requirement("simplejson"),
    requirement("tenacity"),
    requirement("tornado"),
    requirement("ujson"),
    requirement("uvloop"),
    requirement("validators"),
]

REQUIRES = [
    "aiohttp",
    "aiozipkin",
    "atlassian-python-api",
    "bcrypt",
    "cloudaux",
    "cryptography",
    "debugpy",
    "deepdiff",
    "ed25519",
    "email_validator",
    "furl",
    "gitpython",
    "jsonschema",
    "marshmallow",
    "okta",
    "okta-jwt",
    "pandas",
    "parliament",
    "password_strength",
    "policy_sentry",
    "policyuniverse",
    "ptvsd",
    "pyjwt",
    "pytest",
    "requests",
    "retrying",
    "sentry_sdk",
    "simplejson",
    "tenacity",
    "tornado",
    "ujson",
    "uvloop",
]

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)


py_binary(
    name = "bin",
    data = [
        "//configs/development_account:configs",
        "//configs:fluent-bit",
        "//frontend:build",
        ":docs_sources",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    main = "__main__.py",
    env = {
        # Get this by including it (via data = []) and then searching for it: `find -L . -iname "saas_development.yaml"`
        # Note: `bazel info --show_make_env` will show all available predefined variables
        # "CONFIG_LOCATION": "$(GENDIR)/api/bin.runfiles/cloudumi/configs/development_account/saas_development.yaml",
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_cluster_dev",
        "AWS_REGION": "us-west-2",
        "FRONTEND_PATH": "frontend/build",
        "RUNTIME_PROFILE": "API",
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin-no-frontend",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    main = "__main__.py",
    env = {
        # Get this by including it (via data = []) and then searching for it: `find -L . -iname "saas_development.yaml"`
        # Note: `bazel info --show_make_env` will show all available predefined variables
        # "CONFIG_LOCATION": "$(GENDIR)/api/bin.runfiles/cloudumi/configs/development_account/saas_development.yaml",
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_cluster_dev",
        "AWS_REGION": "us-west-2",
        "FRONTEND_PATH": "frontend/build",
        "RUNTIME_PROFILE": "API",
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_api",
    python_tag = "py3",
    version = "0.0.1",
    deps = [":lib"],
    requires = REQUIRES,
    strip_path_prefixes = [
    ],
)

py_layer(
    name = "lib_layer",
    filter = "@",
    deps = [":lib"],
)

py_layer(
    name = "dep_layer",
    filter = "@",
    deps = EXT_DEPS,
)

py_layer(
    name = "int_dep_layer",
    filter = "@",
    deps = INT_DEPS,
)

container_image(
    name = "base-api-dev-local",
    base = "//docker/base:base_docker",
    env = {
        "TZ": "America/Los_Angeles",
        "CONFIG_LOCATION": "/configs/development_account/saas_development.yaml",
        "NOQ_CONTAINER": "1",
        "AWS_PROFILE": "NoqSaasRoleLocalDev",
        "DEBUG": "1",
        "RUNTIME_PROFILE": "API",
    },
    layers = [
        "//deploy/layers:config",
        "//deploy/layers:web_site",
        "//deploy/layers:api.sshd_config",
        "//deploy/layers:weep",
    ],
    volumes = [
        "~/.aws:/root/.aws",
        "~/.weep:/root/.weep",
    ],
    ports = ["8092", "2222"],
    symlinks = {
        "/usr/bin/python": "/usr/local/bin/python",
    },
    data_path = "/",
    docker_run_flags = "-v ~/.aws:/root/.aws -v ~/.weep:/root/.weep",
)

container_image(
    name = "base-api-image",
    base = "//docker/base:base_docker",
    env = {
        "NOQ_CONTAINER": "1",
        "DEBUG": "1",
        "RUNTIME_PROFILE": "API",
    },
    layers = [
        "//deploy/layers:config",
        "//deploy/layers:web_site",
        "//deploy/layers:api.sshd_config",
        "//deploy/layers:weep",
    ],
    ports = ["8092", "2222"],
    data_path = "/",
    symlinks = {
        "/usr/bin/python": "/usr/local/bin/python",
    },
)

py3_image(
    name = "container-dev-local",
    base = ":base-api-dev-local",
    srcs = [
        ":lib",
    ],
    layers = [
        ":dep_layer",
        ":int_dep_layer",
    ],
    deps = EXT_DEPS + INT_DEPS,
    main = "__main__.py",
    visibility = ["//visibility:public"],
)

py3_image(
    name = "container",
    base = ":base-api-image",
    srcs = [
        ":lib",
    ],
    layers = [
        ":dep_layer",
        ":int_dep_layer",
    ],
    deps = EXT_DEPS + INT_DEPS,
    main = "__main__.py",
    tags = ["manual"],
    visibility = ["//visibility:public"]
)