def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    b = path_parts.pop(0)
    k = "/".join(path_parts)
    return b, k
