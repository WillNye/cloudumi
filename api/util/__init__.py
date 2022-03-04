def get_web_response(
    status: str = "success", status_code: int = 200, message: str = ""
):
    return WebResponse(
        status=status,
        status_code=status_code,
        message=message,
    )
