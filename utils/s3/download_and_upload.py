from utils.file_handling.sanitize_object_name import sanitize_object_name
from utils.video_downloader import download_video_task
from utils.s3.upload_to_s3 import upload_to_s3_and_get_url
from utils.file_handling.hash_generator import generate_url_hash
from utils.s3.get_s3_client import get_s3_client
import os

s3_client = get_s3_client()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")


def check_file_exists_in_s3(hash_key: str) -> bool:
    """
    Check if a file exists in S3 using the hash key and has minimum size of 1MB

    :param hash_key: The hash key to check
    :return: True if file exists and is >= 1MB, False otherwise
    """
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=hash_key)
        if "Contents" in response and len(response["Contents"]) > 0:
            # Check if any file is at least 1MB (1048576 bytes)
            for obj in response["Contents"]:
                if obj["Size"] >= 1048576:  # 1MB in bytes, if not overwrite it
                    return True
        return False
    except Exception as e:
        print(f"Error checking S3: {str(e)}")
        return False


def download_file_and_upload_to_s3(url, client_id=None):
    print(f"Worker starting to process URL: {url}")
    try:
        # Generate hash for the URL
        url_hash = generate_url_hash(url)
        print(f"URL hash: {url_hash}")

        # Check if file already exists in S3
        if check_file_exists_in_s3(url_hash):
            print(f"File already exists in S3 for URL: {url}")
            return {
                "success": True,
                "url_hash": url_hash,
                "message": "File already exists",
            }

        # Download the file if it doesn't exist
        download_req = download_video_task(url, client_id)

        if (
            download_req
            and "allowed" in download_req
            and not download_req.get("allowed")
        ):
            print(f"Download not allowed for URL: {url}")
            return download_req
        # Check if download was successful
        elif not download_req or not download_req.get("success"):
            print(f"Download failed for URL: {url}")
            return {
                "success": False,
                "error": download_req.get("error", "Unknown error"),
            }

        # Upload the downloaded file to blob Storage
        filename = download_req.get("filename")
        if filename:
            print(f"Download successful, uploading to S3: {filename}")
            # Use hash as prefix for the file name
            # Sanitize and create a unique object name
            extension = os.path.splitext(filename)[1]
            sanitized_name = sanitize_object_name(
                download_req.get("title", "") + extension
            )
            unique_object_name = f"{url_hash}_{sanitized_name}"

            upload_result = upload_to_s3_and_get_url(
                filename,
                unique_object_name,
                download_directory=download_req.get("download_directory"),
            )

            if upload_result:
                print(f"Successfully processed URL: {url}")
                return {"success": True, "unique_object_name": unique_object_name}

        return {"success": False, "error": "Failed to upload file!"}
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return {"success": False, "error": str(e)}
