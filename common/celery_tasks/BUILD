load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package","py_wheel")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer", "container_push")
#load("@rules_pkg//:pkg.bzl", "pkg_tar")

filegroup(
    name = "src_files",
    srcs = (
        "__init__.py",
        "celery_tasks.py",
        "run.py",
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
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins:lib",
        "//plugins/auth:lib",
        "//plugins/celery_tasks:lib",
        "//plugins/config:lib",
        "//plugins/metrics:lib",
        "//util/log:lib",
        requirement("celery"),
        requirement("ujson"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.local",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
        #"CONFIG_LOCATION": "$(RULEDIR)/configs/development_account:saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = [
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins:lib",
        "//plugins/auth:lib",
        "//plugins/celery_tasks:lib",
        "//plugins/config:lib",
        "//plugins/metrics:lib",
        "//util/log:lib",
        requirement("celery"),
        requirement("ujson"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.s3",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src_files",
    ],
    main = "run.py",
    env = {
        "CONFIG_LOCATION": "s3://noq-tenant-configuration.node.dev1.259868150464.us-west-2/tenant_configurations/saas_development.yaml",
        "AWS_PROFILE": "noq_dev"
    },
    deps = [
        requirement("celery"),
        requirement("ujson"),
    ],
    visibility = ["//visibility:public"],
)

py_package(
    name = "lib_pkg",
    deps = [
        ":lib",
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins:lib",
        "//plugins/auth:lib",
        "//plugins/celery_tasks:lib",
        "//plugins/config:lib",
        "//plugins/metrics:lib",
        "//util/log:lib",
        requirement("amqp"),
        requirement("asgiref"),
        requirement("billiard"),
        requirement("celery"),
        requirement("certifi"),
        requirement("click"),
        requirement("kombu"),
        requirement("okta"),
        requirement("pydantic"),
        requirement("pytz"),
        requirement("PyYAML"),
        requirement("ruamel.yaml"),
        requirement("sentry_sdk"),
        requirement("tornado"),
        requirement("typing_extensions"),
        requirement("ujson"),
        requirement("urllib3"),
        requirement("vine"),
    ],
    packages = [
        "common",
        "common.celery_tasks",
        "common.config",
        "common.exception",
        "identity",
        "plugins",
        "plugins.auth",
        "plugins.celery_tasks",
        "plugins.config",
        "plugins.metrics",
        "util.log",
        "amqp",
        "asgiref",
        "billiard",
        "celery",
        "certifi",
        "click",
        "kombu",
        "okta",
        "pydantic",
        "pytz",
        "PyYAML",
        "ruamel.yaml",
        "sentry_sdk",
        "tornado",
        "typing_extensions",
        "ujson",
        "urllib3",
        "vine",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_common_celery_tasks",
    python_tag = "py3",
    version = "0.0.1",
    # entry_points = {
    #     "console_scripts": [""],
    # },
    deps = [":lib_pkg"],
    requires = ["celery", "ujson"],
    strip_path_prefixes = [
    ],
)

container_layer(
    name = "lib_layer",
    files = [
        ":lib",
    ],
    data_path = ".",
    directory = "/common/celery_tasks",
)

container_layer(
    name = "pkg_layer",
    files = [
        ":lib_pkg",
    ],
    data_path = ".",
    directory = ".",
)

container_layer(
    name = "config_layer",
    files = [
        "//configs/development_account:configs",
    ],
    data_path = ".",
    directory = ".",
)

container_image(
    name = "container-dev-local",
    base = "//docker/base:base_docker",
    layers = [
        ":lib_layer",
        ":pkg_layer",
        ":config_layer",
    ],
    env = {
        "TZ": "America/Los_Angeles",
        "PYTHONPATH": "PYTHONPATH:/usr/lib/python3/dist-packages:/usr/local/lib/python3.9:/usr/lib/python3.9",
        "CONFIG_LOCATION": "/configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    cmd = ["/usr/local/bin/python3", "run.py"],
    ports = [],
    symlinks = {
        "amqp": "cloudumi_python_ext_pypi__amqp/amqp",
        "asgiref": "cloudumi_python_ext_pypi__asgiref/asgiref",
        "billiard": "cloudumi_python_ext_pypi__billiard/billiard",
        "celery": "cloudumi_python_ext_pypi__celery/celery",
        "certifi": "cloudumi_python_ext_pypi__certifi/certifi",
        "click": "cloudumi_python_ext_pypi__click/click",
        "kombu": "cloudumi_python_ext_pypi__kombu/kombu",
        "okta": "cloudumi_python_ext_pypi__okta/okta",
        "pydantic": "cloudumi_python_ext_pypi__pydantic/pydantic",
        "pytz": "cloudumi_python_ext_pypi__pytz/pytz",
        "PyYAML": "cloudumi_python_ext_pypi__pyyaml/PyYAML",
        "ruamel": "cloudumi_python_ext_pypi__ruamel_yaml/ruamel",
        "sentry_sdk": "cloudumi_python_ext_pypi__sentry_sdk/sentry_sdk",
        "tornado": "cloudumi_python_ext_pypi__tornado/tornado",
        "typing_extensions.py": "cloudumi_python_ext_pypi__typing_extensions/typing_extensions.py",
        "ujson": "cloudumi_python_ext_pypi__ujson",
        "urllib3": "cloudumi_python_ext_pypi__urllib3/urllib3",
        "vine": "cloudumi_python_ext_pypi__vine/vine",
    },
    tags = ["manual"],
)