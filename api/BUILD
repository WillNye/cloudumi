load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")
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

INT_DEPS = [
    "//api/handlers:lib",
    "//common/celery_tasks:lib",
    "//common/config:lib",
    "//common/handlers:lib",
    "//identity:lib",
    "//plugins:lib",
    "//plugins/auth:lib",
    "//plugins/celery_tasks:lib",
    "//plugins/config:lib",
    "//plugins/group_mapping:lib",
    "//plugins/metrics:lib",
    "//util/debug",
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
    requirement("newrelic"),
    requirement("okta"),
    requirement("okta-jwt"),
    requirement("pandas"),
    requirement("parliament"),
    requirement("password_strength"),
    requirement("policy_sentry"),
    requirement("policyuniverse"),
    requirement("ptvsd"),
    requirement("pyjwt"),
    requirement("python3-saml"),
    requirement("requests"),
    requirement("retrying"),
    requirement("sentry_sdk"),
    requirement("simplejson"),
    requirement("tenacity"),
    requirement("tornado"),
    requirement("ujson"),
    requirement("uvloop"),
    requirement("xmlsec"),
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
    "newrelic",
    "okta",
    "okta-jwt",
    "pandas",
    "parliament",
    "password_strength",
    "policy_sentry",
    "policyuniverse",
    "pyjwt",
    "python3-saml",
    "ptvsd",
    "requests",
    "retrying",
    "sentry_sdk",
    "simplejson",
    "tenacity",
    "tornado",
    "ujson",
    "uvloop",
    "xmlsec",
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
    name = "bin.local",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    main = "debug.py",
    env = {
        # Get this by including it (via data = []) and then searching for it: `find -L . -iname "saas_development.yaml"`
        # Note: `bazel info --show_make_env` will show all available predefined variables
        # "CONFIG_LOCATION": "$(GENDIR)/api/bin.local.runfiles/cloudumi/configs/development_account/saas_development.yaml",
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.s3",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    main = "__main__.py",
    env = {
        "CONFIG_LOCATION": "s3://noq-tenant-configuration.node.dev1.259868150464.us-west-2/tenant_configurations/saas_development.yaml",
        "AWS_PROFILE": "noq_dev"
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_api",
    python_tag = "py3",
    version = "0.0.1",
    deps = [":lib_pkg"],
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

container_layer(
    name = "config_layer",
    files = [
        "//configs/development_account:configs",
    ],
    data_path = ".",
    directory = "/",
)

container_image(
    name = "base-api-dev-local",
    base = "//docker/base:base_docker",
    env = {
        "TZ": "America/Los_Angeles",
        "PYTHONPATH": "/app/",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "CONFIG_LOCATION": "/configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    layers = [
        ":config_layer",
    ],
    ports = ["8092"],
    symlinks = {
        "/usr/bin/python": "/usr/local/bin/python",
    },
    docker_run_flags = "-v ~/.aws:/root/.aws",
)

container_image(
    name = "base-api-image",
    base = "//docker/base:base_docker",
    env = {
        "TZ": "America/Los_Angeles",
        "PYTHONPATH": "/app/",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    },
    layers = [
        ":config_layer",
    ],
    ports = ["8092"],
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
    name = "container-api",
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
)

container_push(
    name = "container-deploy-staging",
    format = "Docker",
    repository = "cloudumi-api",
    image = "container-api",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "staging",
    visibility = ["//visibility:public"],
)

container_push(
    name = "container-deploy-prod",
    format = "Docker",
    repository = "cloudumi-api",
    image = "container-api",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "prod",
    visibility = ["//visibility:public"],
)