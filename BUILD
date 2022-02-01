load("@io_bazel_rules_docker//docker/util:run.bzl", "container_run_and_commit")
#load("@io_bazel_rules_docker//container:container.bzl", "container_layer")
#load("@cloudumi_python_ext//:requirements.bzl", "requirement")
#load("@rules_pkg//:pkg.bzl", "pkg_tar")

container_run_and_commit(
    name = "cloudumi_base_docker",
    commands = [
        "mkdir -p /apps",
        "apt-get update -y",
        "apt-get install curl telnet iputils-ping sudo vim systemctl apt-transport-https -y",
        "wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -",
        "echo 'deb https://artifacts.elastic.co/packages/7.x/apt stable main' | sudo tee -a /etc/apt/sources.list.d/elastic-7.x.list",
        "sudo apt-get update && sudo apt-get install logstash",
        "systemctl enable logstash",
        "systemctl start logstash",

        # Metricsbeat (System metrics)
        "curl -L -O https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-7.14.2-amd64.deb",
        "dpkg -i metricbeat-7.14.2-amd64.deb",
        "rm -rf metricbeat-7.14.2-amd64.deb",

        "addgroup --gid 1111 appgroup",
        "adduser -uid 1111 --gid 1111 --disabled-password --no-create-hom --gecos '' appuser && chown -R appuser /apps",
        "mkdir -p /home/appuser/.aws",
        "chown -R appuser /home/appuser",
    ],
    # Example of using select
    # image = select({
    #     "//:amd64": "@python_3.9.7_container//image",
    #     "//:arm64": "@python_3.9.7_container//image",
    #     "//:aarch64": "@python_3.9.7_container//image",
    #     "//conditions:default": "@python_3.9.7_container//image",
    # }),
    image = "@python_3.9.7_container//image",
    visibility = ["//visibility:public"],
)