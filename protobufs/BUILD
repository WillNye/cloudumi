load("@rules_proto//proto:defs.bzl", "proto_library")

filegroup(
    name = "proto_files",
    srcs = glob([
        "*.proto",
    ]),
)

proto_library(
    name = "protos",
    srcs = [
        ":proto_files",
    ],
    deps = ["@com_google_protobuf//:timestamp_proto"],
)
