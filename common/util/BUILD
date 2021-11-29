load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer")
load("@io_bazel_rules_docker//docker/util:run.bzl", "container_run_and_commit")

container_layer(
    name = "cloudumi_common_layer",
    data_path = "/cloudumi_common",
    directory = "/apps",
    files = [
    ],
)

container_layer(
    name = "cloudumi_config_layer",
    files = [
    ],
)

container_image(
    name = "cloudumi_common_docker",
    base = "//cloudumi_base_docker:cloudumi_base_docker",
    layers = [
    ],
    workdir = "/apps/cloudumi_common",
    env = {
        "CONFIG_LOCATION": "/apps/cloudumi_config/configs/localhost/saas_development.yaml",
    },
    visibility = ["//visibility:public"],
)