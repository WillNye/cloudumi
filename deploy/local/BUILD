genrule(
    name = "containers-dev",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           -f deploy/docker-compose-bazel-containers.yaml \
           up -d' &>$@",
    executable = True,
    outs = [
        "running",
    ],
    exec_tools = [
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

genrule(
    name = "deps-only",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           up -d' &>$@",
    executable = True,
    outs = [
        "running-deps-only",
    ],
    exec_tools = [
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)

genrule(
    name = "kill-deps-only",
    cmd = "echo 'docker-compose -f deploy/docker-compose-dependencies.yaml \
           down -v' &>$@",
    executable = True,
    outs = [
        "kill-deps-only",
    ],
    exec_tools = [
        "//deploy:compose-files",
    ],
    tags = ["manual"],
)
