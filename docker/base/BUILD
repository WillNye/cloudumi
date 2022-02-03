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
        "mkdir ~/.ssh",
        "bash -c 'echo \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQClHPc54DoYiOy/0IMoDte+aYKF5vSF6DK1miSUVfbkaUd7MiRIDLPvOyIBEOk9AfHnkah2ka6gyGl7pSkyrMLqcbfnHWb/0q3nWg/InqXl0c/aqgkZoaN4VJi4ejoBj7jnWFbS7EJLaPJlGIWh1HKxHbswjuxiEDImytojAKpwfgD6qK6J8hb6XZyiyS0nv61g8w+4H71WoxjArgTUxzdmAFubyU0SP7EG4GkESCcDzs/JhO74tNAY8cZbmp2XENvbWGXwgOUrfn2RoWMFZE/9a8k/hGkmrujzA1UPk+os8NcjR1oN+/kPUzn1N0xmS+UYUChYAIirnD2NMMppQfKJ\" > ~/.ssh/authorized_keys'",
        "mkdir -p /var/run/sshd",
        "bash -c 'echo \"export $$(strings /proc/1/environ | grep AWS_CONTAINER_CREDENTIALS_RELATIVE_URI)\" >> /root/.profile",
        "service ssh restart",
        # "apt-get install build-essential curl telnet iputils-ping sudo vim systemctl apt-transport-https pkg-config libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y",
        "apt-get install openssh-server xmlsec1 libxslt1.1 libxmlsec1 libxmlsec1-dev libxmlsec1-gcrypt libxmlsec1-gnutls libxmlsec1-nss libxmlsec1-openssl -y",
        "pip install uvloop xmlsec",
        # "wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -",
        # "echo 'deb https://artifacts.elastic.co/packages/7.x/apt stable main' | sudo tee -a /etc/apt/sources.list.d/elastic-7.x.list",
        # "sudo apt-get update && sudo apt-get install -y logstash",
        # "systemctl enable logstash",
        # "systemctl start logstash",

        # Metricsbeat (System metrics)
        # "curl -L -O https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-7.14.2-amd64.deb",
        # "dpkg -i metricbeat-7.14.2-amd64.deb",
        # "rm -rf metricbeat-7.14.2-amd64.deb",
    ],
    # Example of using select
    # image = select({
    #     "//:amd64": "@python_3.9.7_container//image",
    #     "//:arm64": "@python_3.9.7_container//image",
    #     "//:aarch64": "@python_3.9.7_container//image",
    #     "//conditions:default": "@python_3.9.7_container//image",
    # }),
    image = "@python_3.9.7_container//image",
    # image = "@python_3.8.12_container//image",
    visibility = ["//visibility:public"],
)

# TODO: let's do without this
container_run_and_commit(
    name = "base_docker_raw_alpine",
    commands = [
        "apk update",
        "apk add build-base libressl libffi-dev libressl-dev libxslt-dev libxml2-dev xmlsec-dev xmlsec",
        # "wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -",
        # "echo 'deb https://artifacts.elastic.co/packages/7.x/apt stable main' | sudo tee -a /etc/apt/sources.list.d/elastic-7.x.list",
        # "sudo apt-get update && sudo apt-get install -y logstash",
        # "systemctl enable logstash",
        # "systemctl start logstash",

        # Metricsbeat (System metrics)
        # "curl -L -O https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-7.14.2-amd64.deb",
        # "dpkg -i metricbeat-7.14.2-amd64.deb",
        # "rm -rf metricbeat-7.14.2-amd64.deb",
    ],
    # Example of using select
    # image = select({
    #     "//:amd64": "@python_3.9.7_container//image",
    #     "//:arm64": "@python_3.9.7_container//image",
    #     "//:aarch64": "@python_3.9.7_container//image",
    #     "//conditions:default": "@python_3.9.7_container//image",
    # }),
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
