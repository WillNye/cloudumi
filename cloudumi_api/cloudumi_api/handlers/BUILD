filegroup(
    name = "src",
    srcs = [
        "__init__.py",
        "auth.py",
    ]
)

filegroup(
    name = "v1",
    srcs = [
        ":src",
        "//cloudumi_api/cloudumi_api/handlers/v1:src",
    ],
)

filegroup(
    name = "v2",
    srcs = [
        ":src",
        "//cloudumi_api/cloudumi_api/handlers/v2/src",
    ]
)

filegroup(
    name = "v3",
    srcs = [
        ":src",
        "//cloudumi_api/cloudumi_api/handlers/v3/src",
    ]
)