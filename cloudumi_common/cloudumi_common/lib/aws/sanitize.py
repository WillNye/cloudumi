import re


def sanitize_session_name(unsanitized_session_name):
    """
    This function sanitizes the session name typically passed in an assume_role call, to verify that it's
    """

    valid_characters_re = r"[\w+=,.@-]"

    sanitized_session_name = ""
    max_length = 64  # Session names have a length limit of 64 characters
    for char in unsanitized_session_name:
        if len(sanitized_session_name) == max_length:
            break
        if re.match(valid_characters_re, char):
            sanitized_session_name += char
    return sanitized_session_name
