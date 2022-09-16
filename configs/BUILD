filegroup(
    name = "filebeat",
    srcs = [
        "filebeat/filebeat.yml",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "fluent-bit",
    srcs = [
        "fluent-bit/fluent-bit.conf",
        "fluent-bit/parsers.conf",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "home",
    srcs = glob([
        "home/**/*",
    ]),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "logstash",
    srcs = glob([
        "logstash/**/*",
    ]),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "metricbeat",
    srcs = [
        "metricbeat/metricbeat.yml",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "newrelic",
    srcs = [
        "newrelic/newrelic.ini",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "ssh",
    srcs = glob([
        "ssh/**/*",
    ]),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "td-agent-bit",
    srcs = glob([
        "td-agent-bit/**/*",
    ]),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "zelkova",
    srcs = [
        "//configs/zelkova",
    ],
    visibility = ["//visibility:public"],
)
