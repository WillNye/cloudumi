from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from dateutil.tz import tzlocal

from functional_tests.conftest import TEST_USER_DOMAIN_US, FunctionalTest


def list_all_objects_version(bucket_name, prefix_name, max_keys=1000):
    session = boto3.session.Session()
    s3_client = session.client("s3")
    try:
        return s3_client.list_object_versions(
            Bucket=bucket_name, Prefix=prefix_name, MaxKeys=max_keys
        )
    except ClientError as e:
        raise Exception(
            "boto3 client error in list_all_objects_version function: " + e.__str__()
        )
    except Exception as e:
        raise Exception(
            "Unexpected error in list_all_objects_version function of s3 helper: "
            + e.__str__()
        )


class TestS3VersionHistory(FunctionalTest):
    def test_get_version_history(self):

        now = datetime.now(tzlocal())
        credential_mapping_versions = list_all_objects_version(
            self.config.get(
                "_global_.s3_cache_bucket",
                "cloudumi-cache.staging-noq-dev-shared-staging-1",
            ),
            f"{TEST_USER_DOMAIN_US}/credential_authorization_mapping/credential_authorization_mapping_v1.json.gz",
            max_keys=6,
        )
        # Assert that the last 5 versions are less than an hour old
        for version in credential_mapping_versions["Versions"][:5]:
            difference = now - version["LastModified"]
            self.assertLess(difference.seconds, 3600)
