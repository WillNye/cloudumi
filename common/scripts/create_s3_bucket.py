"""
Creates an S3 bucket. TODO: Specify server-side encryption with custom KMS key or AWS managed key.

# Example invocation:

AWS_PROFILE=personal python create_s3_bucket.py --bucket noq-tenant-configuration.node.dev1.259868150464.us-west-2 \
     --region us-west-2 --versioning
"""

import boto3
import click


@click.command()
@click.option("--bucket", help="S3 bucket to create")
@click.option("--region", help="Region in which to create the bucket")
@click.option(
    "--versioning/--no-versioning", help="Region in which to create the bucket"
)
# @click.option('--encryption/--no-encryption', help='Whether or not to enable server-side encryption')
# @click.option('--encryption-kms-id', default=None,
#               help='Encryption KMS ID. If server-side encryption is enabled and this is not specified, '
#                    'defaults to an AWS-managed key')
def create_bucket(bucket, region, versioning):
    s3_client = boto3.client("s3", region_name=region)
    location = {"LocationConstraint": region}
    s3_client.create_bucket(Bucket=bucket, CreateBucketConfiguration=location)
    if versioning:
        s3_client.put_bucket_versioning(
            Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
        )

    # if encryption:
    #     s3_client.put_bucket_encryption(
    #         Bucket=bucket,
    #         ServerSideEncryptionConfiguration={
    #             'Rules': [
    #                 {
    #                     'ApplyServerSideEncryptionByDefault': {
    #                         'SSEAlgorithm': 'AES256' | 'aws:kms',
    #                         'KMSMasterKeyID': 'string'
    #                     }
    #                 },
    #             ]
    #         }
    #     )


if __name__ == "__main__":
    create_bucket()
