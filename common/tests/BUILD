load("@cloudumi_python_ext//:requirements.bzl", "requirement")

py_library(
    name = "lib",
    srcs = [
        "globals.py",
        "util.py",
    ],
    visibility = ["//visibility:public"],
)

py_test(
    name = "tests",
    data = [
        "//configs/development_account:configs",
    ],
    srcs = [
        "celery_tasks/test_celery.py",
        "config/test_config.py",
        "handlers/v2/test_aws_iam_users.py",
        "handlers/v2/test_errors.py",
        "handlers/v2/test_generate_changes.py",
        "handlers/v2/test_policies.py",
        "handlers/v2/test_requests.py",
        "handlers/v2/test_roles.py",
        "handlers/v2/test_typeahead.py",
        "handlers/v2/test_user.py",
        "handlers/v2/test_user_profile.py",
        "handlers/test_accessui.py",
        "handlers/test_base.py",
        "handlers/test_policies.py",
        "handlers/test_role_login_api.py",
        "handlers/test_users.py",
        "lib/role_updater/test_handler.py",
        "lib/test_cloud_credential_authorization_mapping/test_cloud_credential_authorization_mapping.py",
        "lib/test_aws.py",
        "lib/test_change_request.py",
        "lib/test_generic.py",
        "lib/test_policies.py",
        "lib/test_requests_v2.py",
        "plugins/test_auth.py",
        "plugins/test_celery_tasks.py",
        "__init__.py",
        "globals.py",
        "test_main.py",
        "util.py",
    ],
    env = {
        "CONFIG_LOCATION": "configs/development_account/saas_local_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    main = "test_main.py",
    deps = [
        "//common:lib",
        "//common/config:lib",
        "//common/exceptions:lib",
        "//identity:lib",
        "//plugins/metrics:lib",
        requirement("asgiref"),
        requirement("tornado"),
    ],
)