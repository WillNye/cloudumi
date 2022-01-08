import sys
import uuid
from datetime import datetime, timedelta

import pytz
import tornado.escape
import ujson as json

from common.config import config
from common.exceptions.exceptions import MissingConfigurationValue
from common.handlers.base import BaseHandler, TornadoRequestHandler
from common.lib.challenge import delete_expired_challenges, retrieve_user_challenge
from common.lib.jwt import generate_jwt_token
from common.lib.redis import RedisHandler

log = config.get_logger()


class ChallengeGeneratorHandler(TornadoRequestHandler):
    """
    Challenge URLs are an alternative to mutual TLS for authenticating CLI clients of ConsoleMe.

    If Challenge Token auth is enabled, this will generate time-sensitive challenge token urls that end-users
    will be required to authenticate to. One authentication is verified, clients will be able to retrieve a
    signed jwt that clients will be able to pass to ConsoleMe for authn/authz.

    The ChallengeUrlGenerator endpoint must be unauthenticated because the CLI client will be requesting URLs
    """

    def get_request_ip(self):
        host = self.get_host_name()
        trusted_remote_ip_header = config.get_host_specific_key(
            "auth.remote_ip.trusted_remote_ip_header", host
        )
        if trusted_remote_ip_header:
            return self.request.headers[trusted_remote_ip_header].split(",")[0]
        return self.request.remote_ip

    async def get(self, user):
        host = self.get_host_name()
        if not config.get_host_specific_key("challenge_url.enabled", host, False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        ip = self.get_request_ip()
        red = await RedisHandler().redis(host)

        token = str(uuid.uuid4())
        entry = {
            "ttl": int(
                (
                    datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(minutes=2)
                ).timestamp()
            ),
            "ip": ip,
            "status": "pending",
            "user": user,
        }
        red.hset(
            config.get_host_specific_key(
                "challenge_url.redis_key",
                host,
                f"{host}_TOKEN_CHALLENGES_TEMP",
            ),
            token,
            json.dumps(entry),
        )

        challenge_url = "{url}/challenge_validator/{token}".format(
            url=config.get_host_specific_key("url", host),
            token=token,
        )
        polling_url = "{url}/noauth/v1/challenge_poller/{token}".format(
            url=config.get_host_specific_key("url", host),
            token=token,
        )
        self.write({"challenge_url": challenge_url, "polling_url": polling_url})

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "challenge_url": challenge_url,
            "polling_url": polling_url,
            "message": "Incoming request",
            "ip": ip,
            "user": user,
            "host": host,
        }
        log.debug(log_data)


class ChallengeValidatorHandler(BaseHandler):
    """

    This is the challenge authentication endpoint.
    Once the user has authenticated successfully, we validate their information and mark the challenge as successful.

    """

    async def get(self, requested_challenge_token):
        host = self.ctx.host
        if not config.get_host_specific_key("challenge_url.enabled", host, False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        red = await RedisHandler().redis(host)
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "requested_challenge_token": requested_challenge_token,
            "message": "Incoming request",
            "ip": self.ip,
        }
        log.debug(log_data)

        all_challenges = red.hgetall(
            config.get_host_specific_key(
                "challenge_url.redis_key",
                host,
                f"{host}_TOKEN_CHALLENGES_TEMP",
            )
        )
        if not all_challenges:
            message = (
                "Unable to find a matching challenge URL. This usually means that it has expired. "
                "Please try requesting a new challenge URL."
            )
            self.write({"message": message})
            return

        await delete_expired_challenges(all_challenges, host)

        valid_user_challenge = await retrieve_user_challenge(
            self, requested_challenge_token, log_data, host
        )
        if not valid_user_challenge:
            return

        if valid_user_challenge.get("visited"):
            message = (
                "This unique challenge URL has already been viewed. "
                "Please try requesting a new challenge URL."
            )
            self.write({"message": message})
            return

        request_ip = self.get_request_ip()

        # By default, the challenge URL requester IP must match the URL the challenge was created with. In some cases
        # (i.e. IPv4 vs IPv6), the challenge may have been created with an IPv4 address, and the authenticated browser
        # verification request may originate from an IPv6 one, or visa versa, in which case this configuration may
        # need to be explicitly set to False.
        if config.get_host_specific_key(
            "challenge_url.request_ip_must_match_challenge_creation_ip",
            host,
            True,
        ):
            if request_ip != valid_user_challenge.get("ip"):
                log.error(
                    {
                        **log_data,
                        "request_ip": request_ip,
                        "challenge_ip": valid_user_challenge.get("ip"),
                        "message": "Request IP doesn't match challenge IP",
                        "host": host,
                    }
                )
                self.write(
                    {
                        "message": (
                            "Your originating IP doesn't match the IP the challenge was created with. "
                            "If you are developing locally, this is probably because your CLI (Weep) made an IPv6 "
                            "request, and your web browser made an IPv4 request. Or visa-versa. If this is the case, "
                            "set the local configuration for "
                            "**challenge_url.request_ip_must_match_challenge_creation_ip** to **false**."
                        )
                    }
                )
                return

        valid_user_challenge["visited"] = True
        valid_user_challenge["nonce"] = str(uuid.uuid4())
        red.hset(
            config.get_host_specific_key(
                "challenge_url.redis_key",
                host,
                f"{host}_TOKEN_CHALLENGES_TEMP",
            ),
            requested_challenge_token,
            json.dumps(valid_user_challenge),
        )

        request_ip = valid_user_challenge["ip"]
        request_user = valid_user_challenge["user"]
        message = (
            f"A user at **{request_ip}** has requested ConsoleMe credentials for **{request_user}**.\n\n"
            f"You must approve this request for credentials to be provided. "
            f"You will not be able to refresh or revisit this page after closing it.\n\n"
            f"If you did not create this request, please report it to your security team."
        )

        self.write(
            {
                "message": message,
                "nonce": valid_user_challenge["nonce"],
                "show_approve_button": True,
            }
        )

    async def post(self, requested_challenge_token):
        host = self.ctx.host
        if not config.get_host_specific_key("challenge_url.enabled", host, False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        red = await RedisHandler().redis(host)
        data = tornado.escape.json_decode(self.request.body)

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "requested_challenge_token": requested_challenge_token,
            "message": "Incoming request",
            "ip": self.ip,
            "host": host,
        }
        log.debug(log_data)

        all_challenges = red.hgetall(
            config.get_host_specific_key(
                "challenge_url.redis_key",
                host,
                f"{host}_TOKEN_CHALLENGES_TEMP",
            )
        )
        if not all_challenges:
            message = (
                "Unable to find a matching challenge URL. This usually means that it has expired. "
                "Please try requesting a new challenge URL."
            )
            self.write({"message": message})
            return

        await delete_expired_challenges(all_challenges, host)

        valid_user_challenge = await retrieve_user_challenge(
            self, requested_challenge_token, log_data, host
        )
        if not valid_user_challenge:
            message = (
                "Unable to find a matching challenge URL. This usually means that it has expired. "
                "Please try requesting a new challenge URL."
            )
            self.write({"message": message})
            return

        if data.get("nonce") != valid_user_challenge["nonce"]:
            message = "Unable to validate challenge URL. The Nonce you've submitted is invalid."
            log.error({**log_data, "message": message})
            self.write({"message": message})
            return

        request_ip = self.get_request_ip()

        # By default, the challenge URL requester IP must match the URL the challenge was created with. In some cases
        # (i.e. IPv4 vs IPv6), the challenge may have been created with an IPv4 address, and the authenticated browser
        # verification request may originate from an IPv6 one, or visa versa, in which case this configuration may
        # need to be explicitly set to False.
        if config.get_host_specific_key(
            "challenge_url.request_ip_must_match_challenge_creation_ip",
            host,
            True,
        ):
            if request_ip != valid_user_challenge.get("ip"):
                log.error(
                    {
                        **log_data,
                        "request_ip": request_ip,
                        "challenge_ip": valid_user_challenge.get("ip"),
                        "message": "Request IP doesn't match challenge IP",
                        "host": host,
                    }
                )
                self.write(
                    {
                        "message": "Your originating IP doesn't match the IP the challenge was created with."
                    }
                )
                return

        valid_user_challenge["status"] = "success"
        valid_user_challenge["user"] = self.user
        valid_user_challenge["groups"] = self.groups
        red.hset(
            config.get_host_specific_key(
                "challenge_url.redis_key",
                host,
                f"{host}_TOKEN_CHALLENGES_TEMP",
            ),
            requested_challenge_token,
            json.dumps(valid_user_challenge),
        )
        message = "You've successfully authenticated to ConsoleMe and may now close this page."
        self.write({"message": message})


class ChallengePollerHandler(TornadoRequestHandler):
    """
    This endpoint is an unauthenticated endpoint that the client uses to poll for successful challenge completion.
    If the challenge has been completed successfully, and the IP of the endpoint matches the IP used to generate the
    challenge URL, we return a signed jwt. It is expected that the client will poll this endpoint continuously until
    the challenge url has been validated by a client, or until it has expired.
    """

    async def get(self, requested_challenge_token):
        host = self.get_host_name()
        if not config.get_host_specific_key("challenge_url.enabled", host, False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        red = await RedisHandler().redis(host)
        challenge_j = red.hget(
            config.get_host_specific_key(
                "challenge_url.redis_key",
                host,
                f"{host}_TOKEN_CHALLENGES_TEMP",
            ),
            requested_challenge_token,
        )
        if not challenge_j:
            self.write({"status": "unknown"})
            return
        challenge = json.loads(challenge_j)

        # Delete the token if it has expired
        current_time = int(datetime.utcnow().replace(tzinfo=pytz.UTC).timestamp())
        if challenge.get("ttl", 0) < current_time:
            red.hdel(
                config.get_host_specific_key(
                    "challenge_url.redis_key",
                    host,
                    f"{host}_TOKEN_CHALLENGES_TEMP",
                ),
                requested_challenge_token,
            )
            self.write({"status": "expired"})
            return

        ip = self.get_request_ip()

        if config.get_host_specific_key(
            "challenge_url.request_ip_must_match_challenge_creation_ip",
            host,
            True,
        ):
            if ip != challenge.get("ip"):
                self.write({"status": "unauthorized"})
                return

        # Generate a jwt if user authentication was successful
        if challenge.get("status") == "success":
            jwt_expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
                minutes=config.get_host_specific_key(
                    "jwt.expiration_minutes", host, 1440
                )
            )
            encoded_jwt = await generate_jwt_token(
                challenge.get("user"), challenge.get("groups"), host, exp=jwt_expiration
            )

            self.write(
                {
                    "status": challenge["status"],
                    "cookie_name": config.get(
                        "_global_.auth.cookie.name", "consoleme_auth"
                    ),
                    "expiration": int(jwt_expiration.timestamp()),
                    "encoded_jwt": encoded_jwt,
                    "user": challenge["user"],
                }
            )
            # Delete the token so that it cannot be re-used
            red.hdel(
                config.get_host_specific_key(
                    "challenge_url.redis_key",
                    host,
                    f"{host}_TOKEN_CHALLENGES_TEMP",
                ),
                requested_challenge_token,
            )
            return
        self.write({"status": challenge.get("status")})
        return
