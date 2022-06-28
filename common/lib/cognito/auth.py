# # TODO: Make this work for
#
import base64
import hashlib
import hmac

import boto3

from common.config import config


def get_secret_hash(username, client_id, client_secret):
    msg = username + client_id
    dig = hmac.new(
        str(client_secret).encode("utf-8"),
        msg=str(msg).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    d2 = base64.b64encode(dig).decode()
    return d2


def initiate_auth(tenant, username, password):
    client = boto3.client("cognito-idp")
    user_pool_id = config.get_tenant_specific_key(
        "secrets.cognito.config.user_pool_id", tenant
    )
    if not user_pool_id:
        raise Exception("User pool is not defined")
    client_id = config.get_tenant_specific_key(
        "secrets.cognito.config.user_pool_client_id", tenant
    )
    if not client_id:
        raise Exception("Client ID is not defined")
    client_secret = config.get_tenant_specific_key(
        "secrets.cognito.config.user_pool_client_secret", tenant
    )
    if not client_secret:
        raise Exception("Client secret is not defined")
    secret_hash = get_secret_hash(username, client_id, client_secret)
    try:
        resp = client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": username,
                "SECRET_HASH": secret_hash,
                "PASSWORD": password,
            },
            ClientMetadata={
                "username": username,
                "password": password,
            },
        )
    except client.exceptions.NotAuthorizedException:
        return None, "The username or password is incorrect"
    except client.exceptions.UserNotConfirmedException:
        return None, "User is not confirmed"
    except Exception as e:
        return None, e.__str__()
    return resp, None


#
# @app.route('/auth/login', methods=['POST'])
# def login():
#     event = auth.current_request.json_body
#     client = boto3.client('cognito-idp')
#     username = event['username']
#     password = event['password']
#     for field in ["username", "password"]:
#         if event.get(field) is None:
#             return {"error": True,
#                     "success": False,
#                     "message": f"{field} is required",
#                     "data": None}
#     resp, msg = initiate_auth(client, username, password)
#     if msg != None:
#         return {'message': msg,
#                 "error": True, "success": False, "data": None}
#     if resp.get("AuthenticationResult"):
#         return {'message': "success",
#                 "error": False,
#                 "success": True,
#                 "data": {
#                     "id_token": resp["AuthenticationResult"]["IdToken"],
#                     "refresh_token": resp["AuthenticationResult"]["RefreshToken"],
#                     "access_token": resp["AuthenticationResult"]["AccessToken"],
#                     "expires_in": resp["AuthenticationResult"]["ExpiresIn"],
#                     "token_type": resp["AuthenticationResult"]["TokenType"]
#                 }}
#     else:  # this code block is relevant only when MFA is enabled
#         return {"error": True,
#                 "success": False,
#                 "data": None, "message": None}
