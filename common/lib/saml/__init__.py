import datetime
import sys

import tornado.httputil
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from furl import furl
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.errors import OneLogin_Saml2_Error
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

from common.config import config
from common.config.config import dict_merge
from common.config.tenant_config import TenantConfig
from common.exceptions.exceptions import WebAuthNError
from common.lib.asyncio import aio_wrapper
from common.lib.generic import should_force_redirect
from common.lib.storage import TenantFileStorageHandler

log = config.get_logger()


async def init_saml_auth(request, tenant):
    tenant_storage = TenantFileStorageHandler(tenant)
    tenant_config = TenantConfig(tenant)
    idp_metadata_url = config.get_tenant_specific_key(
        "get_user_by_saml_settings.idp_metadata_url", tenant
    )
    idp_metadata = {}
    if idp_metadata_url:
        idp_metadata = OneLogin_Saml2_IdPMetadataParser.parse_remote(idp_metadata_url)

    saml_config = dict_merge(tenant_config.saml_config, idp_metadata)

    if not (
        await tenant_storage.tenant_file_exists(tenant_config.saml_key_path)
        and await tenant_storage.tenant_file_exists(tenant_config.saml_cert_path)
    ):

        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # TODO: Need file handler to prevent colissions
        # Write our key to disk for safe keeping
        private_key = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        await tenant_storage.write_file(tenant_config.saml_key_path, "wb", private_key)

        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Noq"),
                x509.NameAttribute(
                    NameOID.COMMON_NAME, "{}".format(tenant_config.tenant_base_url)
                ),
            ]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName("tenant_config.tenant_base_url")]
                ),
                critical=False,
                # Sign our certificate with our private key
            )
            .sign(key, hashes.SHA256())
        )

        encoded_cert = cert.public_bytes(serialization.Encoding.PEM)
        await tenant_storage.write_file(
            tenant_config.saml_cert_path, "wb", encoded_cert
        )

    auth = await aio_wrapper(
        OneLogin_Saml2_Auth,
        request,
        saml_config,
        custom_base_path=await tenant_storage.get_tenant_file_path(
            tenant_config.saml_certificate_folder
        ),
    )
    return auth


def get_saml_login_endpoint(saml_login_endpoint, tenant):
    redirect_uri_f = furl(saml_login_endpoint)
    additional_request_parameters = config.get_tenant_specific_key(
        "get_user_by_saml_settings.additional_saml_request_parameters",
        tenant,
        {},
    )
    for k, v in additional_request_parameters.items():
        redirect_uri_f.args[k] = v
    return redirect_uri_f.url


async def prepare_tornado_request_for_saml(request, tenant):
    dataDict = {}

    for key in request.arguments:
        dataDict[key] = request.arguments[key][0].decode("utf-8")
    redirect_uri = dataDict.get("redirect_url")
    redirect_path = request.path
    redirect_port = tornado.httputil.split_host_and_port(tenant)[1]
    if redirect_uri:
        parsed_redirect_uri = furl(redirect_uri)
        redirect_path = parsed_redirect_uri.pathstr
        redirect_port = parsed_redirect_uri.port
    result = {
        "https": "on" if request == "https" else "off",
        "http_host": tornado.httputil.split_host_and_port(tenant)[0],
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
    tenant = request.get_tenant_name()
    saml_req = await prepare_tornado_request_for_saml(request.request, tenant)
    saml_auth = await init_saml_auth(saml_req, tenant)
    force_redirect = await should_force_redirect(request.request)
    try:
        await aio_wrapper(saml_auth.process_response)
    except OneLogin_Saml2_Error as e:
        log_data["error"] = e
        log.error(log_data)
        login_endpoint = get_saml_login_endpoint(
            saml_auth.login(return_to=saml_req.get("get_data", {}).get("redirect_url")),
            tenant,
        )
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

    saml_errors = await aio_wrapper(saml_auth.get_errors)
    if saml_errors:
        log_data["error"] = saml_errors
        log.error(log_data)
        raise WebAuthNError(reason=saml_errors)

    # We redirect the user to the login page if they are still not authenticated by this point
    not_auth_warn = not await aio_wrapper(saml_auth.is_authenticated)
    if not_auth_warn:
        login_endpoint = get_saml_login_endpoint(saml_auth.login(), tenant)
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
