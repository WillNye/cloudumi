load("//util/tests:defs.bzl", "pytest_test")

pytest_test(
    name = "tests",
    deps = [
        "//common/tests:test_files",
        "//common/lib/cognito/tests:test_files",
        "//common/config/tests:test_files",
    ],
    whitelist = [
        "common",
        "api",
    ],
)
