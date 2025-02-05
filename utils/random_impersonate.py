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
