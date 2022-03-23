import os
import sys
from typing import List

import boto3
import semver

ELASTIC_REGISTRIES = [
    "940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api",
    "940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-celery",
]


def get_registry_name(registry_url: str) -> str:
    return registry_url.split("/")[-1]


def get_image_tags(registry_name: str) -> List[semver.VersionInfo]:
    client = boto3.client("ecr", region_name=os.getenv("AWS_REGION", "us-west-2"))
    image_info = client.list_images(repositoryName=registry_name)
    return [
        semver.VersionInfo.parse(x)
        for x in [y.get("imageTag") for y in image_info.get("imageIds", [])]
        if "." in x
    ]


if __name__ == "__main__":
    version = None
    if len(sys.argv) == 1:
        version = os.getenv("ROLLBACK_VERSION")
    elif len(sys.argv) == 2:
        version = sys.argv[1]
    else:
        print(f"Syntax: {sys.argv[0]} <rollback_version>")

    if version is None:
        resolved_versions = dict()
        for registry in ELASTIC_REGISTRIES:
            registry_name = get_registry_name(registry)
            resolved_versions[registry_name] = get_image_tags(registry_name)
        try:
            rollback_candidate_versions = {
                x: y
                for x in ELASTIC_REGISTRIES
                for y in resolved_versions[get_registry_name(x)][-2]
            }
        except IndexError:
            raise RuntimeError(
                f"Unable to rollback, no other versions other than {resolved_versions[get_registry_name(ELASTIC_REGISTRIES[0])][0]}"
            )

        rollback_candidate_version = {x for x in rollback_candidate_versions.values()}
        if len(rollback_candidate_version) > 1:
            raise RuntimeError(
                f"Inconsistent versioning, more handholding is required {rollback_candidate_version}"
            )
    else:
        rollback_candidate_version = [version]

    os.environ["VERSION"] = rollback_candidate_version[0]
    print(f"Rolling back to version: {rollback_candidate_version[0]}")
    answer = input("Are you sure? y/n or CTRL+C to exit")

    if answer in ["y", "Y"]:
        import ecs_deployer  # noqa
