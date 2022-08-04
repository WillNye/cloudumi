load("@io_bazel_rules_docker//container:container.bzl", "container_layer")

container_layer(
    name = "config",
    files = [
        "//configs/development_account:configs",
    ],
    data_path = ".",
    directory = "/",
)

container_layer(
    name = "web_site",
    files = [
        "//frontend:build",
        ":docs_sources",
    ],
    data_path = ".",
    directory = "/",
)

container_layer(
    name = "api.sshd_config",
    files = [
        "//configs/ssh/api:sshd_config",
    ],
    directory = "/etc/ssh",
)

container_layer(
    name = "celery_tasks.sshd_config",
    files = [
        "//configs/ssh/celery_tasks:sshd_config",
    ],
    directory = "/etc/ssh",
)

container_layer(
    name = "newrelic",
    files = [
        "//configs/newrelic:newrelic.ini",
    ],
    directory = "/etc/newrelic",
)

container_layer(
    name = "weep",
    files = [
        "@weep//file",
    ],
    directory = "/usr/bin",
)

