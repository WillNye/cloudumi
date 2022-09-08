import uuid

import sentry_sdk
import tornado.escape

from common.config import config
from common.config.models import ModelAdapter
from common.handlers.base import BaseHandler
from common.lib.auth import is_tenant_admin
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent_bit"))()
log = config.get_logger()


class ConfigurationCrudHandler(BaseHandler):
    """
    Provides generic CRUD capabilities for configuration items that are specifically tied to a pydantic model
    """

    _model_class = None
    _config_key = None
    _identifying_keys = list()
    _triggers = list()

    @classmethod
    def __validate_class_vars(cls):
        if not cls._model_class or not cls._config_key:
            raise RuntimeError(f"{cls.__name__} is not properly configured")

    async def _retrieve(self) -> dict:
        return (
            ModelAdapter(self._model_class)
            .load_config(self._config_key, self.ctx.tenant)
            .dict
        )

    async def _create(self, data):
        await ModelAdapter(self._model_class).load_config(
            self._config_key, self.ctx.tenant
        ).from_dict(data).with_object_key(self._identifying_keys).store_item()

    async def _delete(self) -> bool:
        return (
            await ModelAdapter(self._model_class)
            .load_config(self._config_key, self.ctx.tenant)
            .with_object_key(self._identifying_keys)
            .delete_key()
        )

    async def get(self):
        tenant = self.ctx.tenant
        self.__validate_class_vars()

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "model_class": self._model_class,
            "config_key": self._config_key,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = f"Cannot call GET on {type(self).__name__}"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        try:
            get_data = await self._retrieve()
            res = WebResponse(
                success="success" if get_data else "error",
                status_code=200,
                message="Success" if get_data else "Unable to retrieve data",
                count=1 if get_data else 0,
            )
        except ValueError:
            get_data = None
            res = WebResponse(
                success="error",
                status_code=404,
                message=f"Desired entry {self._config_key} not found",
                count=0,
            )
        except Exception as exc:
            get_data = None
            res = WebResponse(
                success="error",
                status_code=500,
                message=f"Something went wrong {str(exc)}",
                count=0,
            )
            sentry_sdk.capture_exception()
        # hub_account_data is a special structure, so we unroll it
        if get_data:
            res.data = get_data

        for trigger in self._triggers:
            log.info(f"Applying trigger {trigger.name}")
            trigger.apply_async((self.ctx.__dict__,))

        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        self.__validate_class_vars()
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Updating data",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "model_class": self._model_class,
            "config_key": self._config_key,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = f"Unable to call POST on {type(self).__name__}"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        external_id = config.get_tenant_specific_key(
            "tenant_details.external_id", tenant
        )
        data["external_id"] = external_id

        try:
            await self._create(data)
        except Exception as exc:
            log.error(exc, exc_info=True)
            res = WebResponse(
                success="error",
                status_code=400,
                message="Invalid body data received",
                errors=str(exc).split("\n"),
            )
            sentry_sdk.capture_exception()
        else:
            res = WebResponse(
                status="success",
                status_code=200,
                message="Successfully updated",
            )

        for trigger in self._triggers:
            log.info(f"Applying trigger {trigger.name}")
            trigger.apply_async((self.ctx.__dict__,))

        self.write(res.json(exclude_unset=True, exclude_none=True))
        return

    async def delete(self):
        self.__validate_class_vars()
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Deleting data",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "model_class": self._model_class,
            "config_key": self._config_key,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete data"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        try:
            deleted = await self._delete()
            res = WebResponse(
                status="success" if deleted else "error",
                status_code=200 if deleted else 400,
                message="Successfully deleted data."
                if deleted
                else "Unable to delete data.",
            )

            if deleted:
                for trigger in self._triggers:
                    log.info(f"Applying trigger {trigger.name}")
                    trigger.apply_async((self.ctx.__dict__,))

        except KeyError as exc:
            log.error(exc, exc_info=True)
            res = WebResponse(
                success="error",
                status_code=400,
                message="Unable to delete data",
                errors=[f"Unable to find {self._config_key}"],
            )

        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class MultiItemConfigurationCrudHandler(BaseHandler):
    """
    Provides generic CRUD capabilities for list-based configuration items that are specifically tied to a pydantic model

    The difference between the MultiItemConfigurationCrudHandler and the ConfigurationCrudHandler can be summarized as follows:

    ConfigurationCrudHandler: auth.sso.google - config key gets one config item at this key
    MultiItemConfigurationCrudHandler: aws.cognito.account.users - config key gets cruds ops operating on a list

    This means a few things:
    * each insertion checks first if an identical item exists
    * each deletion merely removes an items from the list, versus removing the key
    * each get call will *always* return a list
    """

    _model_class = None
    _config_key = None
    _identifying_keys = list()
    _triggers = list()

    @classmethod
    def __validate_class_vars(cls):
        if not cls._model_class or not cls._config_key:
            raise RuntimeError(f"{cls.__name__} is not properly configured")

    async def _retrieve(self) -> list[dict]:
        return (
            ModelAdapter(self._model_class)
            .load_config(self._config_key, self.ctx.tenant)
            .list
        )

    async def _create(self, data):
        await ModelAdapter(self._model_class).load_config(
            self._config_key, self.ctx.tenant
        ).from_dict(data).with_object_key(self._identifying_keys).store_item_in_list()

    async def _delete(self, data):
        return (
            await ModelAdapter(self._model_class)
            .load_config(self._config_key, self.ctx.tenant)
            .from_dict(data)
            .with_object_key(self._identifying_keys)
            .delete_list()
        )

    async def get(self):
        tenant = self.ctx.tenant
        self.__validate_class_vars()

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "model_class": self._model_class,
            "config_key": self._config_key,
            "tenant": tenant,
        }
        log.debug(log_data)

        # Checks authz levels of current user
        generic_error_message = f"Cannot call GET on {type(self).__name__}"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        get_data = await self._retrieve()
        # hub_account_data is a special structure, so we unroll it
        res = WebResponse(
            success="success" if get_data else "error",
            status_code=200,
            message="Success" if get_data else "Unable to retrieve data",
            count=len(get_data) if get_data else 0,
        )
        if get_data:
            res.data = get_data

        for trigger in self._triggers:
            log.info(f"Applying trigger {trigger.name}")
            trigger.apply_async((self.ctx.__dict__,))

        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        self.__validate_class_vars()
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Updating data",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "model_class": self._model_class,
            "config_key": self._config_key,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = f"Unable to call POST on {type(self).__name__}"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        external_id = config.get_tenant_specific_key(
            "tenant_details.external_id", tenant
        )
        data["external_id"] = external_id

        # Automatically generate uuid if not provided
        uuid_identifiers = [
            x
            for x in self._identifying_keys
            if self._model_class.schema()
            .get("properties", {})
            .get(x.capitalize(), {})
            .get("format")
            == "uuid"
        ]
        for uuid_identifier in uuid_identifiers:
            if not data.get(uuid_identifier):
                data[uuid_identifier] = str(uuid.uuid4())

        # Note: we are accepting one item posted at a time; in the future we might support
        # multiple items posted at a time
        try:
            await self._create(data)
        except Exception as exc:
            log.error(exc, exc_info=True)
            res = WebResponse(
                success="error",
                status_code=400,
                message="Invalid body data received",
                errors=str(exc).split("\n"),
            )
            sentry_sdk.capture_exception()
        else:
            res = WebResponse(
                status="success",
                status_code=200,
                message="Successfully updated",
            )

        for trigger in self._triggers:
            log.info(f"Applying trigger {trigger.name}")
            trigger.apply_async((self.ctx.__dict__,))

        self.write(res.json(exclude_unset=True, exclude_none=True))
        return

    async def delete(self):
        self.__validate_class_vars()
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Deleting data",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "model_class": self._model_class,
            "config_key": self._config_key,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete data"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        external_id = config.get_tenant_specific_key(
            "tenant_details.external_id", tenant
        )
        data["external_id"] = external_id

        # Note: we are accepting one item posted at a time; in the future we might support
        # multiple items posted at a time
        try:
            deleted = await self._delete(data)
            res = WebResponse(
                status="success" if deleted else "error",
                status_code=200 if deleted else 400,
                message="Successfully deleted data."
                if deleted
                else "Unable to delete data.",
            )
            if deleted:
                for trigger in self._triggers:
                    log.info(f"Applying trigger {trigger.name}")
                    trigger.apply_async((self.ctx.__dict__,))
        except KeyError as exc:
            log.error(exc, exc_info=True)
            res = WebResponse(
                success="error",
                status_code=400,
                message="Unable to delete data",
                errors=[f"Unable to find {self._config_key}"],
            )
        except Exception as exc:
            res = WebResponse(
                success="error",
                status_code=400,
                message="Invalid body data received",
                errors=str(exc).split("\n"),
            )
            sentry_sdk.capture_exception()

        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
