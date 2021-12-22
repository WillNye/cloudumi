genrule(
    name = "containers-dev",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           -f deploy/docker-compose-bazel-containers.yaml \
           up -d' &>$@",
    executable = True,
    outs = [
        "running",
    ],
    srcs = [
        "//api:container-dev-local",
        "//common/celery_tasks:container-dev-local",
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)

genrule(
    name = "containers-dev-kill",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           -f deploy/docker-compose-bazel-containers.yaml \
           down -v' &>$@",
    executable = True,
    outs = [
        "removed",
    ],
    srcs = [
        "//api:container-dev-local",
        "//common/celery_tasks:container-dev-local",
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)
