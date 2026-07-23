import re, os


def sanitize_object_name(object_name: str) -> str:
    """
    Sanitize the object name to allow only safe characters and limit length to 50 chars.

    :param object_name: Original object name
    :return: Sanitized object name
    """
    # First remove unsafe characters
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", object_name)

    # If filename is longer than 50 chars, truncate it
    # We preserve the file extension by splitting and handling separately
    if len(sanitized) > 50:
        name, ext = os.path.splitext(sanitized)
        # Take first (50 - length of extension) characters of the name
        # and append the extension
        max_name_length = 50 - len(ext)
        sanitized = name[:max_name_length] + ext

    return "vidf_" + sanitized
