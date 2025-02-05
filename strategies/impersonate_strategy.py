import yt_dlp
from utils.random_impersonate import random_impersonate_target

class ImpersonateDownloadStrategy:
    def __init__(self, logger):
        self.logger = logger

    def download(self, url: str, options: dict) -> dict:
        """
        Attempt to download a video using impersonation.
        This strategy adds an 'impersonate' option to the yt-dlp options.

        :param url: Video URL
        :param options: yt-dlp options dictionary.
        :return: Download information dictionary (augmented with 'filename').
        :raises Exception: If download fails.
        """
        # Add impersonation option
        options["impersonate"] = random_impersonate_target()
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                # Compute the filename using yt-dlp helper
                info_dict["filename"] = ydl.prepare_filename(info_dict)
                self.logger.info(f"Impersonation download succeeded for URL: {url}")
                return info_dict
        except Exception as e:
            self.logger.error(f"Impersonation download failed for URL {url}: {e}")
            raise
