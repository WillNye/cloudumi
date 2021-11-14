import json
import logging
import requests

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def __return(status: int, msg: str):
    logger.info(f"Returning status {status} with msg {msg}")
    return {
        'statusCode': status,
        'body': json.dumps(msg)
    }

def emit_s3_response(event, context):
    logger.info(f"Called {__name__}")
    try:
        event_dict = json.loads(event)
    except json.decoder.JSONDecodeError:
        return __return(400, "Ignoring non-json event message")
    response_url = event.get('ResponseUrl')
    if not response_url:
        return __return(500, "Invalid response message sent from SNS")
    response_data = {
        "Status": "SUCCESS"
    }
    response_data_json = json.dumps(response_data)
    response_header = {
        "Content-Type": "",
        "Content-Length": str(len(response_data_json))
    }
    logger.info(f"Sending SUCCESS to {response_url}")
    requests.put(response_url, data=response_data_json, headers=response_header)
    return __return(200, "OK")