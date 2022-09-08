load("@io_bazel_rules_docker//docker/util:run.bzl", "container_run_and_commit")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer")

genrule(
    name = "create_tag_file",
    srcs = [
    ],
    stamp = True,
    outs = [ "tag_file" ],
    cmd = "git rev-parse HEAD >> $@",
)

# TODO: let's do without this
container_run_and_commit(
    name = "base_docker_raw",
    commands = [
        "apt-get update -y",
        "apt-get install -y clang build-essential openssh-server cron curl telnet iputils-ping sudo vim systemctl apt-transport-https pkg-config libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev libssl-dev software-properties-common python3-dev nodejs",
        "curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | sh",
        "pip install uvloop awscli",
        "mkdir -p /root/.ssh/",
        "echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQClHPc54DoYiOy/0IMoDte+aYKF5vSF6DK1miSUVfbkaUd7MiRIDLPvOyIBEOk9AfHnkah2ka6gyGl7pSkyrMLqcbfnHWb/0q3nWg/InqXl0c/aqgkZoaN4VJi4ejoBj7jnWFbS7EJLaPJlGIWh1HKxHbswjuxiEDImytojAKpwfgD6qK6J8hb6XZyiyS0nv61g8w+4H71WoxjArgTUxzdmAFubyU0SP7EG4GkESCcDzs/JhO74tNAY8cZbmp2XENvbWGXwgOUrfn2RoWMFZE/9a8k/hGkmrujzA1UPk+os8NcjR1oN+/kPUzn1N0xmS+UYUChYAIirnD2NMMppQfKJ' > ~/.ssh/authorized_keys",
        "echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDJVXcOw8LrbMzWnrY5qW9anu3qXIR7tRpvpAPxeMXgiP6hA+EW4swe/bzo+sMmrfWgMLWw9IdMaoX4mVisVTZj8b3rhgMyouCF8cTejOY/E7uFPs+t3ZvsQidc5adhdK4XsLPNjNOQoMqtjdcZL1yN5PckQkVpXxZ5p1Ei854hwyOU07iR/kuV9Cx8bx+UAyW53SSrlKzQvf+oW7CknDlouxv33SZmruWY/u3lBR90r6Wa0vk032E0DbERFPeTjz2CP6zX+bxLDHH/12+jGdivSQX9j5O/bUDJLOUJhMGGRnTnTfu8qClYE93bpyIRm9zTHx+sv7ITMqGFHzgMC39CcYFC5rmnPAPgjMlYKDuldVRYU2BI7Jad2TRjBQl+aWeQvIFWt5OgpmJHsApVUs8Uz88LyrHRjim3l3KJlnUdHorZidERmyHDPecnUquriK94xFoUE1VR96DeUYM0x0fAfUS1VaN/FvLxP5s+CTgdj5AVT4mV+MOnA4o3gaQ2sXE=' >> ~/.ssh/authorized_keys",
        "mkdir -p /var/run/sshd",
    ],
    image = "@python_3.10_container//image",
    visibility = ["//visibility:public"],
)

container_image(
    name = "base_docker",
    base = ":base_docker_raw",
    layers = [
        "//deploy/layers:zelkova",
        "//deploy/layers:filebeat",
        "//deploy/layers:fluent-bit",
        "//deploy/layers:logstash",
        "//deploy/layers:metricbeat",
        "//deploy/layers:td-agent-bit",
        "//deploy/layers:home",
    ],
    data_path = "/",
    visibility = ["//visibility:public"],
)
