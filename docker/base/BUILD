load("@io_bazel_rules_docker//docker/util:run.bzl", "container_run_and_commit")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer")
#load("@cloudumi_python_ext//:requirements.bzl", "requirement")
#load("@rules_pkg//:pkg.bzl", "pkg_tar")

filegroup(
    name = "etc_files",
    srcs = [
        "root/etc",
    ],
)

filegroup(
    name = "home_files",
    srcs = [
        "root/home",
    ],
)

container_layer(
    name = "etc_layer",
    directory = "/",
    files = [
        ":etc_files",
    ],
)

container_layer(
    name = "home_layer",
    directory = "/",
    files = [
        ":home_files",
    ]
)

# TODO: let's do without this
container_run_and_commit(
    name = "base_docker_raw",
    commands = [
        "apt-get update -y",
        "apt-get install build-essential openssh-server cron curl telnet iputils-ping sudo vim systemctl apt-transport-https pkg-config libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y",
        "pip install uvloop xmlsec awscli",
        "mkdir -p /var/run/sshd",
        "echo \"export $$(strings /proc/1/environ | grep AWS_CONTAINER_CREDENTIALS_RELATIVE_URI)\" >> /root/.profile",
    ],
    image = "@python_3.9.7_container//image",
    visibility = ["//visibility:public"],
)

# TODO: let's do without this
container_run_and_commit(
    name = "base_docker_raw_alpine",
    commands = [
        "apk update",
        "apk add build-base libressl libffi-dev libressl-dev libxslt-dev libxml2-dev xmlsec-dev xmlsec",
    ],
    image = "@python_3.9.7_alpine_container//image",
    visibility = ["//visibility:public"],
)

container_image(
    name = "base_docker",
    base = ":base_docker_raw",
    layers = [
        ":etc_layer",
        ":home_layer",
    ],
    data_path = "/",
    visibility = ["//visibility:public"],
)

container_image(
    name = "base_docker_alpine",
    base = ":base_docker_raw_alpine",
    layers = [
        ":etc_layer",
        ":home_layer",
    ],
    data_path = "/",
    visibility = ["//visibility:public"],
)
