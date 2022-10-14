sh_binary(
    name = "gen_test_certs",
    srcs = ["gen_test_certs.sh"],
    visibility = ["//visibility:public"],
)

genrule(
    name = "test_certs",
    outs = [
        "tests/tls/ca.key",
        "tests/tls/client.crt",
        "tests/tls/client.key",
        "tests/tls/openssl.cnf",
        "tests/tls/redis.crt",
        "tests/tls/redis.dh",
        "tests/tls/redis.key",
        "tests/tls/server.crt",
        "tests/tls/server.key"
    ],
    cmd = "$(location gen_test_certs.sh) $(@D)",
    tools = ["gen_test_certs.sh"],
    executable = False,
    message = "Generating test certs",
    output_to_bindir = True,
    visibility = ["//visibility:public"],
)