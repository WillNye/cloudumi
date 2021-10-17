load("@io_bazel_rules_docker//container:container.bzl", "container_image")

container_layer(
    name = "cloudumi_common_layer",
    srcs = [
        "/cloudumi_common/cloudumi_common:cloudumi_common",
        "/cloudumi_common/cloudumi_plugins:cloudumi_plugins",
    ],
)

container_layer(
    name = "cloudumi_config_layer",
    srcs = [
        ":cloudumi_config",
    ],
)

container_image(
    name = "cloudumi_common_docker_pre",
    base = "/cloudumi_base_docker:cloudumi_base_docker",
    layers = [
        ":cloudumi_common_layer",
        ":cloudumi_config_layer",
    ],
)

container_run_and_commit(
    name = "cloudumi_common_docker_run",
    image = ":cloudumi_common_docker_pre",
    commands = [
        "apt-get update",
        "apt-get install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y",
        "python -m pip install --upgrade pip",
        "pip install /apps/cloudumi_common/",
        "pip install /apps/cloudumi_common/cloudumi_plugins",
        "python -m pip install -r requirements.txt",
        "python -m pip install -e .",
    ],
)

container_image(
    name = "cloudumi_common_docker",
    base = ":cloudumi_common_docker_run",
    workdir = "/apps/cloudumi_common",
    env = {
        "CONFIG_LOCATION": "/apps/cloudumi_config/configs/localhost/saas_development.yaml",
    },
)