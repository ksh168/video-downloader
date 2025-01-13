from flask import jsonify
from downloader.video_downloader import VideoDownloader
from utils.upload_to_s3 import upload_to_s3_and_get_url
import os
from flask import current_app as app

class VideoService:
    def __init__(self, socketio):
        self.socketio = socketio

    def handle_download_request(self, url: str, client_id: str):
        """Handle the video download request and return appropriate response"""
        try:
            download_result = self._download_video(url, client_id)
            
            if not download_result.get("success"):
                return jsonify({
                    "success": False, 
                    "error": download_result.get("error", "Unknown error")
                }), 500

            download_url = self._handle_s3_upload(download_result)
            if download_url:
                return jsonify({"success": True, "download_url": download_url})

            return jsonify({"success": False, "error": "Failed to upload file"}), 500

        except Exception as e:
            app.logger.exception("Unexpected error during download")
            return jsonify({"success": False, "error": str(e)}), 500

    def _download_video(self, url: str, client_id: str) -> dict:
        """Download the video using VideoDownloader"""
        downloader = VideoDownloader(self.socketio)
        downloader.client_id = client_id
        result = downloader.download(url)

        if not result["success"]:
            app.logger.error(f"Download failed: {result.get('error', 'Unknown error')}")
        else:
            app.logger.info(f"Successfully downloaded video: {result['filename']}")

        return result

    def _handle_s3_upload(self, download_result: dict) -> str:
        """Upload the downloaded file to S3 and return the URL"""
        filename = download_result.get("filename")
        if not filename:
            return None

        return upload_to_s3_and_get_url(
            filename,
            os.path.basename(filename),
            download_directory=download_result.get("download_directory")
        ) 