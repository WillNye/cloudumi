import os
import sys
from typing import List

import boto3
from distutils.version import LooseVersion

ELASTIC_REGISTRIES = [
    "775726381634.dkr.ecr.us-west-2.amazonaws.com/cyberdyne-prod-registry-api",
]


def get_registry_name(registry_url: str) -> str:
    return registry_url.split("/")[-1]


def get_image_tags(registry_name: str) -> List[str]:
    client = boto3.client("ecr", region_name=os.getenv("AWS_REGION", "us-west-2"))
    image_info = client.list_images(repositoryName=registry_name)
    return [
        x
        for x in [y.get("imageTag") for y in image_info.get("imageIds", [])]
        if x is not None and "." in x
    ]


if __name__ == "__main__":
    version = None
    if len(sys.argv) == 1:
        version = os.getenv("ROLLBACK_VERSION")
    elif len(sys.argv) == 2:
        version = sys.argv[1]
    else:
        print(f"Syntax: {sys.argv[0]} <rollback_version>")

    rollback_candidate_version = "0.0.0-dev"
    if version is None:
        resolved_versions = {}
        ref_registry_name = None
        for registry in ELASTIC_REGISTRIES:
            registry_name = get_registry_name(registry)
            if ref_registry_name is None:
                ref_registry_name = registry_name
            resolved_versions[registry_name] = sorted(
                get_image_tags(registry_name), key=LooseVersion
            )

        ref_versions = list(
            sorted(
                {
                    x
                    for n in resolved_versions.values()
                    for x in resolved_versions[ref_registry_name]
                    if any(k for k in n if k == x)
                },
                key=LooseVersion,
            )
        )

        rollback_candidate_version = ref_versions[-2]

    else:
        rollback_candidate_version = version

    os.environ["VERSION"] = rollback_candidate_version
    print(f"Rolling back to version: {rollback_candidate_version}")
    answer = input("Are you sure? y/n or CTRL+C to exit")

    if answer in ["y", "Y"]:
        import ecs_deployer  # noqa
