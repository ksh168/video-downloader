from utils.video_downloader import download_video_task
from utils.upload_to_s3 import upload_to_s3_and_get_url
import os


def download_file_and_upload_to_s3(url, client_id=None):
    print(f"Worker starting to process URL: {url}")
    try:
        download_req = download_video_task(url, client_id) 

        # Check if download was successful
        if not download_req.get("success"):
            print(f"Download failed for URL: {url}")
            return {"success": False, "error": download_req.get("error", "Unknown error")}

        # Upload the downloaded file to blob Storage
        filename = download_req.get("filename")
        if filename:
            print(f"Download successful, uploading to S3: {filename}")
            unique_object_name = upload_to_s3_and_get_url(
                filename,
                os.path.basename(filename),
                download_directory=download_req.get("download_directory"),
            )
            if unique_object_name:
                print(f"Successfully processed URL: {url}")
                return {"success": True, "unique_object_name": unique_object_name}

        return {"success": False, "error": "Failed to upload file!"}
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return {"success": False, "error": str(e)}
