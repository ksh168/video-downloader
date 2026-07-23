import yt_dlp

class DirectHitDownloadStrategy:
    def __init__(self, logger):
        self.logger = logger

    def download(self, url: str, options: dict) -> dict:
        """
        Attempt to download a video using a direct hit (without impersonation).

        :param url: Video URL
        :param options: yt-dlp options dictionary (without impersonation).
        :return: Download information dictionary (augmented with 'filename').
        :raises Exception: If download fails.
        """
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                # Compute the filename using yt-dlp helper
                info_dict["filename"] = ydl.prepare_filename(info_dict)
                self.logger.info(f"Direct hit download succeeded for URL: {url}")
                return info_dict
        except Exception as e:
            self.logger.error(f"Direct hit download failed for URL {url}: {e}")
            raise
