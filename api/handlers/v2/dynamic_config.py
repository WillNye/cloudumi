import sys
from hashlib import sha256

import sentry_sdk
import tornado.escape
import tornado.web

import common.lib.noq_json as json
from common.config import config
from common.handlers.base import BaseHandler
from common.lib.asyncio import aio_wrapper
from common.lib.auth import can_edit_dynamic_config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.noq_json import SetEncoder

log = config.get_logger(__name__)


class DynamicConfigApiHandler(BaseHandler):
    def on_finish(self) -> None:
        if self.request.method != "POST":
            return
        from common.celery_tasks.celery_tasks import app as celery_app

        tenant = self.ctx.tenant
        # Force a refresh of credential authorization mapping in current region
        # TODO: Trigger this to run cross-region
        # TODO: Delete server-side user-role cache intelligently so users get immediate access
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            countdown=config.get_tenant_specific_key(
                "dynamic_config.dynamo_load_interval", tenant
            ),
            kwargs={"tenant": tenant},
        )

    async def get(self) -> None:
        """
        Get the dynamic configuration endpoint.
        ---
        description: Presents a YAML-configured editor to allow viewing and modification of dynamic config
        responses:
            200:
                description: View of dynamic configuration
            403:
                description: Unauthorized to access this page
        """

        if not self.user:
            return
        tenant = self.ctx.tenant
        if not can_edit_dynamic_config(self.user, self.groups, tenant):
            raise tornado.web.HTTPError(
                403, "Only application admins are authorized to view this page."
            )
        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            tenant,
            return_format="bytes",
            filter_secrets=True,
        )

        self.write(
            {
                "dynamicConfig": dynamic_config.decode("utf-8"),
                "sha256": sha256(dynamic_config).hexdigest(),
            }
        )

    async def post(self):
        """
        Post an update to the dynamic configuration endpoint.
        ---
        description: Update dynamic configuration
        responses:
            200:
                description: Update successful.
            403:
                description: Unauthorized to access this page
        """

        if not self.user:
            return
        tenant = self.ctx.tenant
        if not can_edit_dynamic_config(self.user, self.groups, tenant):
            raise tornado.web.HTTPError(
                403, "Only application admins are authorized to view this page."
            )
        ddb = RestrictedDynamoHandler()
        existing_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync, tenant, return_format="bytes"
        )
        if existing_config:
            existing_dynamic_config_sha256 = sha256(existing_config).hexdigest()
        else:
            existing_dynamic_config_sha256 = None
        result = {"status": "success"}
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "existing_dynamic_config_sha256": existing_dynamic_config_sha256,
            "tenant": tenant,
        }
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        try:
            # TODO: Figure out change control, hash is manipulated when we filter out secrets
            # existing_sha256 = data.get("existing_sha256")
            new_sha256 = sha256(data["new_config"].encode("utf-8")).hexdigest()
            # if existing_sha256 == new_sha256:
            #     raise Exception(
            #         "You didn't change the dynamic configuration. Try again!"
            #     )
            # if (
            #     existing_dynamic_config_sha256
            #     and not existing_dynamic_config_sha256 == existing_sha256
            # ):
            #     raise Exception(
            #         "Dynamic configuration was updated by another user before your changes were processed. "
            #         "Please refresh your page and try again."
            #     )

            await ddb.update_static_config_for_tenant(
                data["new_config"], self.user, tenant
            )
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"There was an error processing your request: {e}"
            sentry_sdk.capture_exception()
            self.write(json.dumps(result, cls=SetEncoder))
            await self.finish()
            return

        result["newConfig"] = data["new_config"]
        result["newsha56"] = new_sha256
        self.write(result)
        await self.finish()
        return
