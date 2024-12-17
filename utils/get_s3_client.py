import os
import boto3
from botocore.config import Config

from constants import AWS_REGION


def get_s3_client():
    boto_config = Config(
        region_name=AWS_REGION,
        signature_version="s3v4",
    )

    return boto3.client(
        "s3",
        endpoint_url="https://s3.filebase.com",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        config=boto_config,
    )
