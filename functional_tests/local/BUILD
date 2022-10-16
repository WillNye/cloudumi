load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

INT_DEPS = [
    "//common/celery_tasks:lib",
    "//common/config:lib",
    "//common/config/tests:test_files",
    "//common/lib/cognito/tests:test_files",
    "//common/lib",
    "//common/tests:test_files",
    "//functional_tests:lib",
    "//util/log:lib",
]

EXT_DEPS = [
    requirement("boto3"),
    requirement("botocore"),
    requirement("flake8"),
    requirement("moto"),
    requirement("pytest"),
    requirement("pytest-cov"),
    requirement("pytest-mccabe"),
    requirement("pytest-mypy"),
    requirement("tornado"),
    requirement("ujson"),
]

copy_file(
    name = "run_tests",
    src = "//functional_tests:run_tests.py",
    out = "run_tests.py",
    allow_symlink = True,
    visibility = ["//visibility:public"],
)

py_library(
    name = "lib",
    srcs = [
        "//functional_tests:lib",
        "run_tests.py",
    ],
    data = [":run_tests"],
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin",
    data = [
        "//configs/development_account:saas_development.yaml",

    ],
    srcs_version = "PY3",
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_cluster_dev",
        "TEST_USER_DOMAIN": "localhost",
    },
    srcs = [":lib"],
    main = "local/run_tests.py",
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)