load("@io_bazel_rules_docker//container:container.bzl", "container_layer")

container_layer(
    name = "config",
    files = [
        "//configs/development_account:configs",
    ],
    data_path = ".",
    directory = "/",
    visibility = ["//visibility:public"],
)

container_layer(
    name = "zelkova",
    directory = "/root",
    files = [
        "//configs:zelkova",
    ],
    visibility = ["//visibility:public"],
)

container_layer(
    name = "filebeat",
    directory = "/etc/filebeat",
    files = [
        "//configs:filebeat",
    ],
    visibility = ["//visibility:public"],
)

container_layer(
    name = "logstash",
    directory = "/etc/logstash",
    files = [
        "//configs:logstash",
    ],
    visibility = ["//visibility:public"],
)

container_layer(
    name = "metricbeat",
    directory = "/etc/metricbeat",
    files = [
        "//configs:metricbeat",
    ],
    visibility = ["//visibility:public"],
)

container_layer(
    name = "td-agent-bit",
    directory = "/etc/td-agent-bit",
    files = [
        "//configs:td-agent-bit",
    ],
    visibility = ["//visibility:public"],
)

container_layer(
    name = "home",
    directory = "/",
    files = [
        "//configs:home",
    ],
    visibility = ["//visibility:public"],
)

container_layer(
    name = "web_site",
    files = [
        "//frontend:build",
        "//frontend:upload",
        "//api:docs_sources",
    ],
    data_path = ".",
    directory = "/",
    visibility = ["//visibility:public"],
)

container_layer(
    name = "api.sshd_config",
    files = [
        "//configs/ssh/api:sshd_config",
    ],
    directory = "/etc/ssh",
    visibility = ["//visibility:public"],
)

container_layer(
    name = "celery_tasks.sshd_config",
    files = [
        "//configs/ssh/celery_tasks:sshd_config",
    ],
    directory = "/etc/ssh",
    visibility = ["//visibility:public"],
)

container_layer(
    name = "newrelic",
    files = [
        "//configs:newrelic",
    ],
    directory = "/etc/newrelic",
    visibility = ["//visibility:public"],
)

container_layer(
    name = "weep",
    files = [
        "@weep//file",
    ],
    directory = "/usr/bin",
    visibility = ["//visibility:public"],
)
