from yt_dlp import ImpersonateTarget
from random import choice

impersonate_target_list = (
    ImpersonateTarget(client='chrome', version='110', os='windows', os_version='10'),
    ImpersonateTarget(client='chrome', version='107', os='windows', os_version='10'),
    ImpersonateTarget(client='chrome', version='104', os='windows', os_version='10'),
    ImpersonateTarget(client='chrome', version='101', os='windows', os_version='10'),
    ImpersonateTarget(client='chrome', version='100', os='windows', os_version='10'),
    ImpersonateTarget(client='chrome', version='99', os='windows', os_version='10'),
    ImpersonateTarget(client='edge', version='101', os='windows', os_version='10'),
    ImpersonateTarget(client='edge', version='99', os='windows', os_version='10'),
    ImpersonateTarget(client='safari', version='15.5', os='macos', os_version='12'),
    ImpersonateTarget(client='safari', version='15.3', os='macos', os_version='11'),
    ImpersonateTarget(client='chrome', version='99', os='android', os_version='12'),
    ImpersonateTarget.from_str("chrome-99:android-12"),
    ImpersonateTarget.from_str("safari-15.3:macos-11"),
)

def random_impersonate_target():
    """
    Return a random impersonation target
    """
    target: ImpersonateTarget = choice(impersonate_target_list)
    return target

# def download_vimeo_video(vimeo_url):
#     for i in range(200):
#         try:
#             vimeo_urls = [vimeo_url] # .replace("https")]
#             impersonate_as = random_impersonate_target()
#             print(f"Downloading {vimeo_url} as {impersonate_as}")
#             ydl_opts = {
#                 'format': 'best',
#                 "outtmpl": "%(title)s",
#                 "simulate": False,
#                 "verbose": True,
#                 "continue": True,
#                 "impersonate": impersonate_as,
#             }
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 ydl.download(vimeo_urls)
#         except Exception as e:
#             # Print the traceback object
#             traceback.print_tb(e.__traceback__)
#             print(f"Error downloading {vimeo_url}: {str(e)}")
