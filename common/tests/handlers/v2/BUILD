load("@cloudumi_python_ext//:requirements.bzl", "requirement")
load("//util/tests:defs.bzl", "pytest_test")

pytest_test(
    name = "test_aws_iam_users",
    data = [
        "//util/tests:configs",
    ],
    srcs = [
        "test_aws_iam_users.py",
        "test_errors.py",
        "test_generate_changes.py",
        "test_policies_handlers_v2.py",
        "test_requests.py",
        "test_roles.py",
        "test_typeahead.py",
        "test_user_profile.py",
        "test_user.py",
    ],
    deps = [
    ],
)
