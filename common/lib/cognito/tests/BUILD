load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

INT_DEPS = [
    "//common:lib",
    "//common/config:lib",
    "//common/exceptions:lib",
    "//identity:lib",
    "//plugins/metrics:lib",
    "//util/tests/fixtures:lib",
]

EXT_DEPS = [
    requirement("moto")
]

pytest_test(
    name = "test_identity",
    srcs = [
        "test_identity.py",
    ],
    deps = [
    ] + INT_DEPS + EXT_DEPS,
)
