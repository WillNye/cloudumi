load("@rules_python//python:defs.bzl", "py_test")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

def pytest_test(name, srcs = [], args = [], deps = [], data = [], **kwargs):
    """
        Pytest Wrapper to simplify calling pytest for testing
    """
    # whitelist = ",".join(whitelist)
    py_test(
        name = name,
        srcs = [
            "//util/tests:wrapper.py",
            "//util/tests/fixtures:fixtures.py",
            "//util/tests/fixtures:globals.py",
        ],
        main = "//util/tests:wrapper.py",
        args = args,
        python_version = "PY3",
        srcs_version = "PY3",
        deps = deps + [
        #     "//common/celery_tasks:lib",
        #     requirement("boto3"),
        #     requirement("pytest"),
        #     requirement("pytest-asyncio"),
        #     #requirement("pytest-black"),
        #     #requirement("pytest-pylint"),
        #     requirement("redislite"),
        #     requirement("requests-mock"),
        #     # requirement("pytest-mypy"),
        ],
        env = {
            "AWS_REGION": "us-west-2",
            "CONFIG_LOCATION": "util/tests/test_configuration.yaml",
            "AWS_PROFILE": "dev",
        },
        data = [
            "//util/tests:test_configuration.yaml",
        ] + data,
        **kwargs
    )
