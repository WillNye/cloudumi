load("@rules_python//python:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_package", "py_wheel")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_layer")
load("@io_bazel_rules_docker//python:image.bzl", "py_layer")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")
load("@cloudumi_python_ext//:requirements.bzl", "requirement")

filegroup(
    name = "src",
    srcs = [
        "__init__.py",
        "__main__.py",
        "routes.py",
    ]
)

INT_DEPS = [
    "//api/handlers:lib",
    "//common/celery_tasks:lib",
    "//common/config:lib",
    "//common/handlers:lib",
    "//identity:lib",
    "//plugins:lib",
    "//plugins/auth:lib",
    "//plugins/celery_tasks:lib",
    "//plugins/config:lib",
    "//plugins/metrics:lib",
    "//saml:lib",
    "//util/log:lib",
]

EXT_DEPS = [
    requirement("aiohttp"),
    requirement("aiozipkin"),
    requirement("atlassian-python-api"),
    requirement("bcrypt"),
    requirement("cloudaux"),
    requirement("cryptography"),
    requirement("deepdiff"),
    requirement("ed25519"),
    requirement("email_validator"),
    requirement("furl"),
    requirement("gitpython"),
    requirement("jsonschema"),
    requirement("marshmallow"),
    requirement("newrelic"),
    requirement("okta"),
    requirement("okta-jwt"),
    requirement("pandas"),
    requirement("parliament"),
    requirement("password_strength"),
    requirement("policy_sentry"),
    requirement("policyuniverse"),
    requirement("pyjwt"),
    requirement("python3-saml"),
    requirement("requests"),
    requirement("retrying"),
    requirement("sentry_sdk"),
    requirement("simplejson"),
    requirement("tenacity"),
    requirement("tornado"),
    requirement("ujson"),
    requirement("uvloop"),
    requirement("xmlsec"),
]

REQUIRES = [
    "aiohttp",
    "aiozipkin",
    "atlassian-python-api",
    "bcrypt",
    "cloudaux",
    "cryptography",
    "deepdiff",
    "ed25519",
    "email_validator",
    "furl",
    "gitpython",
    "jsonschema",
    "marshmallow",
    "newrelic",
    "okta",
    "okta-jwt",
    "pandas",
    "parliament",
    "password_strength",
    "policy_sentry",
    "policyuniverse",
    "pyjwt",
    "python3-saml",
    "requests",
    "retrying",
    "sentry_sdk",
    "simplejson",
    "tenacity",
    "tornado",
    "ujson",
    "uvloop",
    "xmlsec",
]

py_library(
    name = "lib",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.local",
    data = [
        "//configs/development_account:configs",
    ],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    main = "__main__.py",
    env = {
        # Get this by including it (via data = []) and then searching for it: `find -L . -iname "saas_development.yaml"`
        # Note: `bazel info --show_make_env` will show all available predefined variables
        # "CONFIG_LOCATION": "$(GENDIR)/api/bin.local.runfiles/cloudumi/configs/development_account/saas_development.yaml",
        "CONFIG_LOCATION": "configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_binary(
    name = "bin.s3",
    data = [],
    srcs_version = "PY3",
    srcs = [
        ":src",
    ],
    main = "__main__.py",
    env = {
        "CONFIG_LOCATION": "s3://noq-tenant-configuration.node.dev1.259868150464.us-west-2/tenant_configurations/saas_development.yaml",
        "AWS_PROFILE": "noq_dev"
    },
    deps = INT_DEPS + EXT_DEPS,
    visibility = ["//visibility:public"],
)

py_wheel(
    name = "wheel",
    distribution = "cloudumi_api",
    python_tag = "py3",
    version = "0.0.1",
    # entry_points = {
    #     "console_scripts": [""],
    # },
    deps = [":lib_pkg"],
    requires = REQUIRES,
    strip_path_prefixes = [
    ],
)

py_layer(
    name = "lib_layer",
    filter = "@",
    deps = [":lib"],
)

py_layer(
    name = "dep_layer",
    filter = "@",
    deps = EXT_DEPS,
)

py_layer(
    name = "int_dep_layer",
    filter = "@",
    deps = INT_DEPS,
)

container_layer(
    name = "config_layer",
    files = [
        "//configs/development_account:configs",
    ],
    data_path = ".",
    directory = "/configs",
)

container_image(
    name = "base-api-dev-local",
    base = "//docker/base:base_docker",
    env = {
        "TZ": "America/Los_Angeles",
        "PYTHONPATH": "PYTHONPATH:/usr/lib/python3/dist-packages:/usr/local/lib/python3.9:/usr/lib/python3.9",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "CONFIG_LOCATION": "/configs/development_account/saas_development.yaml",
        "AWS_PROFILE": "noq_dev",
    },
    layers = [
        ":config_layer",
    ],
    ports = ["8092"],
    symlinks = {
        "/usr/bin/python": "/usr/bin/python3",
    }
)

py3_image(
    name = "container-dev-local",
    base = ":base-api-dev-local",
    srcs = [
        ":lib",
    ],
    layers = [
        # ":lib_layer",
        ":dep_layer",
        ":int_dep_layer",
    ],
    main = "__main__.py",
    # symlinks = { 
    #     "amqp": "cloudumi_python_ext_pypi__amqp/amqp",
    #     "aiohttp": "cloudumi_python_ext_pypi__aiohttp/aiohttp",
    #     "aiozipkin": "cloudumi_python_ext_pypi__aiozipkin/aiozipkin",
    #     "atlassian-python-api": "cloudumi_python_ext_pypi__atlassian-python-api/atlassian-python-api",
    #     "asgiref": "cloudumi_python_ext_pypi__asgiref/asgiref",
    #     "bcrypt": "cloudumi_python_ext_pypi__bcrypt/bcrypt",
    #     "billiard": "cloudumi_python_ext_pypi__billiard/billiard",
    #     "celery": "cloudumi_python_ext_pypi__celery/celery",
    #     "certifi": "cloudumi_python_ext_pypi__certifi/certifi",
    #     "cloudaux": "cloudumi_python_ext_pypi__cloudaux/cloudaux",
    #     "click": "cloudumi_python_ext_pypi__click/click",
    #     "cryptography": "cloudumi_python_ext_pypi__cryptography/cryptography",
    #     "deepdiff": "cloudumi_python_ext_pypi__deepdiff/deepdiff",
    #     "ed25519": "cloudumi_python_ext_pypi__ed25519/ed25519",
    #     "furl": "cloudumi_python_ext_pypi__furl/furl",
    #     "gitpython": "cloudumi_python_ext_pypi__gitpython/gitpython",
    #     "isodate": "cloudumi_python_ext_pypi__isodate/isodate",
    #     "jsonschema": "cloudumi_python_ext_pypi__jsonschema/jsonschema",
    #     "kombu": "cloudumi_python_ext_pypi__kombu/kombu",
    #     "lxml": "cloudumi_python_ext_pypi__lxml/lxml",
    #     "newrelic": "cloudumi_python_ext_pypi__newrelic/newrelic",
    #     "okta": "cloudumi_python_ext_pypi__okta/okta",
    #     "okta-jwt": "cloudumi_python_ext_pypi__okta-jwt/okta-jwt",
    #     "onelogin": "cloudumi_python_ext_pypi__python3_saml/onelogin",
    #     "pandas": "cloudumi_python_ext_pypi__pandas/pandas",
    #     "parliament": "cloudumi_python_ext_pypi__parliament/parliament",
    #     "password_strength": "cloudumi_python_ext_pypi__password_strength/password_strength",
    #     "policy_sentry": "cloudumi_python_ext_pypi__policy_sentry/policy_sentry",
    #     "pydantic": "cloudumi_python_ext_pypi__pydantic/pydantic",
    #     "pyjwt": "cloudumi_python_ext_pypi__pyjwt/pyjwt",
    #     #"python3_saml": "cloudumi_python_ext_pypi__python3_saml/python3_saml",
    #     "pytz": "cloudumi_python_ext_pypi__pytz/pytz",
    #     "PyYAML": "cloudumi_python_ext_pypi__pyyaml/PyYAML",
    #     "requests": "cloudumi_python_ext_pypi__requests/requests",
    #     "retrying": "cloudumi_python_ext_pypi__retrying/retrying",
    #     "ruamel": "cloudumi_python_ext_pypi__ruamel_yaml/ruamel",
    #     "sentry_sdk": "cloudumi_python_ext_pypi__sentry_sdk/sentry_sdk",
    #     "simplejson": "cloudumi_python_ext_pypi__simplejson/simplejson",
    #     "tenacity": "cloudumi_python_ext_pypi__tenacity/tenacity",
    #     "tornado": "cloudumi_python_ext_pypi__tornado/tornado",
    #     "typing_extensions.py": "cloudumi_python_ext_pypi__typing_extensions/typing_extensions.py",
    #     "ujson": "cloudumi_python_ext_pypi__ujson",
    #     "urllib3": "cloudumi_python_ext_pypi__urllib3/urllib3",
    #     "uvloop": "cloudumi_python_ext_pypi__uvloop/uvloop",
    #     "vine": "cloudumi_python_ext_pypi__vine/vine",
    #     "xmlsec": "cloudumi_python_ext_pypi__xmlsec/xmlsec",
    # },
    tags = ["manual"],
)