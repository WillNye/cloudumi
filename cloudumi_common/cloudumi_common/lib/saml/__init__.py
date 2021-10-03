import copy
import sys

import tornado.httputil
from asgiref.sync import sync_to_async
from furl import furl
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.errors import OneLogin_Saml2_Error
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

from cloudumi_common.config import config
from cloudumi_common.config.config import dict_merge
from cloudumi_common.exceptions.exceptions import WebAuthNError
from cloudumi_common.lib.generic import should_force_redirect

log = config.get_logger()


async def init_saml_auth(request, host):
    saml_config = copy.deepcopy(
        config.get(f"site_configs.{host}.get_user_by_saml_settings.saml_settings", {})
    )
    idp_metadata_url = config.get(
        f"site_configs.{host}.get_user_by_saml_settings.idp_metadata_url"
    )
    if idp_metadata_url:
        idp_metadata = OneLogin_Saml2_IdPMetadataParser.parse_remote(idp_metadata_url)
        saml_config = dict_merge(saml_config, idp_metadata)
    auth = await sync_to_async(OneLogin_Saml2_Auth)(
        request,
        saml_config,
        custom_base_path=config.get(
            f"site_configs.{host}.get_user_by_saml_settings.saml_path"
        ),
    )
    return auth


def get_saml_login_endpoint(saml_login_endpoint, host):
    redirect_uri_f = furl(saml_login_endpoint)
    additional_request_parameters = config.get(
        f"site_configs.{host}.get_user_by_saml_settings.additional_saml_request_parameters",
        {},
    )
    for k, v in additional_request_parameters.items():
        redirect_uri_f.args[k] = v
    return redirect_uri_f.url


async def prepare_tornado_request_for_saml(request):
    dataDict = {}

    for key in request.arguments:
        dataDict[key] = request.arguments[key][0].decode("utf-8")
    redirect_uri = dataDict.get("redirect_url")
    redirect_path = request.path
    redirect_port = tornado.httputil.split_host_and_port(request.host)[1]
    if redirect_uri:
        parsed_redirect_uri = furl(redirect_uri)
        redirect_path = parsed_redirect_uri.pathstr
        redirect_port = parsed_redirect_uri.port
    result = {
        "https": "on" if request == "https" else "off",
        "http_host": tornado.httputil.split_host_and_port(request.host)[0],
        "script_name": redirect_path,
        "server_port": redirect_port,
        "get_data": dataDict,
        "post_data": dataDict,
        "query_string": request.query,
    }
    return result


async def authenticate_user_by_saml(request):
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}
    # TODO: Start here
    host = request.get_host_name()
    saml_req = await prepare_tornado_request_for_saml(request.request)
    saml_auth = await init_saml_auth(saml_req, host)
    force_redirect = await should_force_redirect(request.request)
    try:
        await sync_to_async(saml_auth.process_response)()
    except OneLogin_Saml2_Error as e:
        log_data["error"] = e
        log.error(log_data)
        login_endpoint = get_saml_login_endpoint(saml_auth.login(), host)
        if force_redirect:
            return request.redirect(login_endpoint)
        else:
            request.set_status(403)
            request.write(
                {
                    "type": "redirect",
                    "redirect_url": login_endpoint,
                    "reason": "unauthenticated",
                    "message": "User is not authenticated. Redirect to authenticate",
                }
            )
            request.finish()
            return

    saml_errors = await sync_to_async(saml_auth.get_errors)()
    if saml_errors:
        log_data["error"] = saml_errors
        log.error(log_data)
        raise WebAuthNError(reason=saml_errors)

    # We redirect the user to the login page if they are still not authenticated by this point
    not_auth_warn = not await sync_to_async(saml_auth.is_authenticated)()
    if not_auth_warn:
        login_endpoint = get_saml_login_endpoint(saml_auth.login(), host)
        if force_redirect:
            return request.redirect(login_endpoint)
        else:
            request.set_status(403)
            request.write(
                {
                    "type": "redirect",
                    "redirect_url": login_endpoint,
                    "reason": "unauthenticated",
                    "message": "User is not authenticated. Redirect to authenticate",
                }
            )
            request.finish()
            return
