load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer")
load("@io_bazel_rules_docker//docker/util:run.bzl", "container_run_and_commit")

container_layer(
    name = "common_layer",
    data_path = "/common",
    directory = "/apps",
    files = [
    ],
)

container_layer(
    name = "config_layer",
    files = [
    ],
)

container_image(
    name = "common_docker",
    base = "//docker/base:base_docker",
    layers = [
    ],
    workdir = "/apps/common",
    env = {
        "CONFIG_LOCATION": "/apps/configs/development_account/saas_local_development.yaml",
    },
    visibility = ["//visibility:public"],
)