load("@build_bazel_rules_nodejs//:index.bzl", "copy_to_bin", "nodejs_binary", "npm_package_bin")
load("@npm//http-server:index.bzl", "http_server")
load("@npm//webpack-cli:index.bzl", webpack = "webpack_cli")

filegroup(
    name = "project_files",
    srcs = [
        "craco.config.js",
        "package.json",
        "README.md",
    ],
    visibility = ["//visibility:public"],
)

nodejs_binary(
    name = "craco_bin",
    entry_point = "@npm//node_modules/@craco/craco/bin/craco.js",
    templated_args = [
        "build",
    ]
)

copy_to_bin(
    name = "source_files_in_bin",
    srcs = [
        "//frontend/src",
        ":project_files",
    ],
)

# npm_package_bin(
#     name = "bundle",
#     outs = ["app.bundle.js"],
#     data = [
#         ":source_files_in_bin",
#         "@npm//:node_modules",
#     ],
#     tool = ":craco_bin",
# )

webpack(
    name = "bundle",
    outs = ["app.bundle.js"],
    args = [
        "bundle",
        "$(execpath src/index.js)",
        "--config",
        "$(execpath src/webpack.config.js)",
        "-o",
        "$@",
    ],
    data = [
        "//frontend/src:index.js",
        "//frontend/src:webpack.config.js",
        "@npm//:node_modules",
        "source_files_in_bin",
    ],
)

# Note, on Windows you need `--enable_runfiles`
http_server(
    name = "server",
    data = [
        "app.bundle.js",
        "index.html",
    ],
    templated_args = ["."],
)