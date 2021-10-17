load("@io_bazel_rules_docker//container:container.bzl", "container_image")

container_image(
    name = "container",
    base = "//:alpine_base_server_image",
    files = [
        ":lib",
        ":video_frame_files",
    ],
    env = {
        "TZ": "America/Los_Angeles",
        "PYTHONPATH": "PYTHONPATH:/usr/lib/python3/dist-packages:/usr/local/lib/python3.9:/usr/lib/python3.9",
    },
    cmd = ["/usr/local/bin/python3", "run.py"],
    ports = ["50051", "50052"],
    #entrypoint = "./entrypoint.sh",
    data_path = "/opt/rapta/video_capture",
    workdir = "/opt/rapta/video_capture",
    symlinks = { 
        "/opt/rapta/video_capture": "/components/sensor/video_frame_capture",
    },
    tags = ["manual"],
)