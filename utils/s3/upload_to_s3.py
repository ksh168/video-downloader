from typing import Optional
from botocore.exceptions import ClientError
import re
import os
from uuid import uuid4

from utils.file_handling.delete_local_file import delete_local_file
from utils.s3.get_s3_client import get_s3_client

s3_client = get_s3_client()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")


def get_s3_presigned_url(bucket_name: str, object_name: str) -> Optional[str]:
    """
    Generate a presigned URL to share an S3 object

    :param bucket_name: S3 bucket name
    :param object_name: S3 object name
    :return: Presigned URL as string. If error, returns None.
    """
    try:
        # Generate URL that expires in 2 hours
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=7200,  # 2 hours
        )
        return response
    except ClientError as e:
        print(f"Failed to generate presigned URL: {str(e)}")
        return None


def upload_file_to_s3(file_path: str, object_name: str) -> Optional[str]:
    """
    Upload a file to S3 with a unique name.

    :param file_path: Path to the file to upload
    :param object_name: Name of the object in S3
    :return: The unique object name used in S3
    """
    try:
        print(f"Uploading to S3, Bucket: {S3_BUCKET_NAME}")

        # Upload the file
        s3_client.upload_file(file_path, S3_BUCKET_NAME, object_name)

        print(f"File {file_path} uploaded to S3 as {object_name}.")
        return True
    except Exception as e:
        print(f"Failed to upload {file_path} to S3: {e}")
        return False


def upload_to_s3_and_get_url(
    file_path: str, object_name: str, download_directory: str
) -> Optional[str]:
    """
    Upload a file to S3 and return a presigned URL for download.

    :param file_path: Path to the file to upload
    :param object_name: Name of the object in S3
    :param download_directory: Directory to download the file to
    :return: Presigned URL for the uploaded object
    """
    upload_file_req = upload_file_to_s3(file_path, object_name)
    if upload_file_req:
        # presigned_url = get_s3_presigned_url(S3_BUCKET_NAME, uploaded_object_name)

        delete_local_file(download_directory)

        # return presigned_url
        return True
    return None