from typing import Optional


def delete_local_file(download_directory: str) -> Optional[str]:
    """
    Delete a local file at the specified path.

    Args:
        download_directory: Directory to delete if the file is in it
    Returns:
        Optional[str]: Error message if deletion failed, None if successful
    """
    try:
        if download_directory:
            import shutil

            shutil.rmtree(download_directory)
            print(f"Successfully deleted directory: {download_directory}")
            return None
        else:
            return f"Directory not found: {download_directory}"
    except Exception as e:
        error_msg = f"Failed to delete directory {download_directory}: {str(e)}"
        print(error_msg)
        return error_msg
