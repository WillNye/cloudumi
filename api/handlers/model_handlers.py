import asyncio
import uuid
from functools import wraps
from typing import Coroutine

import sentry_sdk
import tornado.escape

from common.config import config
from common.config.models import ModelAdapter
from common.handlers.base import BaseHandler
from common.lib.asyncio import aio_wrapper
from common.lib.auth import is_tenant_admin
from common.lib.dictutils import get_in, set_in
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.lib.yaml import yaml
from common.models import Status2, WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


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
        self.set_header("Content-Type", "application/json")

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
        if get_data is not None:
            res.data = get_data

        for trigger in self._triggers:
            log.info(f"Applying trigger {trigger.name}")
            trigger.apply_async((self.ctx.__dict__,))
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        self.__validate_class_vars()
        tenant = self.ctx.tenant
        self.set_header("Content-Type", "application/json")

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
        self.set_header("Content-Type", "application/json")

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
        self.set_header("Content-Type", "application/json")
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
        if get_data is not None:
            res.data = get_data

        for trigger in self._triggers:
            log.info(f"Applying trigger {trigger.name}")
            trigger.apply_async((self.ctx.__dict__,))

        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        self.__validate_class_vars()
        tenant = self.ctx.tenant
        self.set_header("Content-Type", "application/json")

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
        self.set_header("Content-Type", "application/json")

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
        self.set_status(res.status_code)
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


def handle_request(func):
    """Decorator to handle common actions for a request. This includes pre-request
    processing, checking if the user is an admin, applying triggers post processing
    if applicable, and handling exceptions.

    Args:
        func (Callable): The function to wrap. This function should be an asynchronous
            method of a `BaseConfigurationCrudHandler` instance.

    Returns:
        Callable: The decorated function.
    """

    @wraps(func)
    async def wrapper(self: "BaseConfigurationCrudHandler", *args, **kwargs):
        log_data = await self.pre_request()
        await self.is_not_admin(log_data)

        try:
            result = await func(self, *args, **kwargs)

            if result:
                await self._apply_triggers()
        except Exception as exc:
            log.error(exc, exc_info=True)
            res = WebResponse(
                status=Status2.error,
                status_code=400,
                reason=None,
                message="Invalid body data received",
                errors=str(exc).split("\n"),
            )
            sentry_sdk.capture_exception()
            self.write(res.json(exclude_unset=True, exclude_none=True))

    return wrapper


class BaseConfigurationCrudHandler(BaseHandler):
    """
    Base class for CRUD operations on configurations.
    Child classes should implement the abstract methods.
    """

    _model_class = None
    _config_key: str
    _triggers = list()

    def _validate_vars(self):
        pass

    async def _retrieve(self):
        """Placeholder method for retrieving data. Should be overridden by child classes."""
        raise NotImplementedError

    async def _create(self, data):
        """Placeholder method for creating data. Should be overridden by child classes."""
        raise NotImplementedError

    async def _update(self, data):
        """Placeholder method for updating data. Should be overridden by child classes."""
        raise NotImplementedError

    async def _delete(self, data):
        """Placeholder method for deleting data. Should be overridden by child classes."""
        raise NotImplementedError

    async def _get_body_data(self):
        """Placeholder method for getting data from the request body. Should be overridden by child classes."""
        raise NotImplementedError

    async def pre_request(self, **kwargs):
        """Perform actions before the request is processed, including validating variables and logging."""
        self._validate_vars()

        message = ""

        match self.request.method:
            case "GET":
                message = "Retrieving information"
            case "POST":
                message = "Inserting data"
            case "PUT":
                message = "Updating data"
            case "DELETE":
                message = "Deleting data"

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": message,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "model_class": self._model_class,
            "config_key": self._config_key,
            "tenant": self.ctx.tenant,
        } | kwargs

        log.debug(log_data)

        return log_data

    async def _apply_triggers(self):
        """Apply all triggers for this handler."""
        tasks: list[Coroutine] = [
            trigger.apply_async((self.ctx.__dict__,)) for trigger in self._triggers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def is_not_admin(self, log_data):
        """Checks if the current user is not a tenant admin."""
        if not is_tenant_admin(
            self.user,
            self.groups,
            self.ctx.tenant,
        ):
            generic_error_message = (
                f"Cannot call {self.request.method} on {type(self).__name__}"
            )
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            log.debug(log_data)
            raise tornado.web.Finish()

    @handle_request
    async def get(self):
        get_data = await self._retrieve()
        self.set_header("Content-Type", "application/json")

        # hub_account_data is a special structure, so we unroll it
        res = WebResponse(
            status=Status2.success if get_data else Status2.error,
            status_code=200,
            reason=None,
            message="Success" if get_data else "Unable to retrieve data",
            count=len(get_data) if get_data else 0,
        )

        if get_data is not None:
            res.data = get_data

        self.write(res.json(exclude_unset=True, exclude_none=True))
        return get_data

    @handle_request
    async def post(self):
        data = await self._get_body_data()
        result = await self._create(data)
        self.set_header("Content-Type", "application/json")

        res = WebResponse(
            status=Status2.success,
            status_code=200,
            reason=None,
            message="Successfully updated",
        )

        self.write(res.json(exclude_unset=True, exclude_none=True))
        return result

    @handle_request
    async def put(self):
        data = await self._get_body_data()
        self.set_header("Content-Type", "application/json")

        await self._update(data)

        res = WebResponse(
            status=Status2.success,
            status_code=200,
            reason=None,
            message="Successfully updated",
        )

        self.write(res.json(exclude_unset=True, exclude_none=True))
        return data

    @handle_request
    async def delete(self):
        data = await self._get_body_data()
        self.set_header("Content-Type", "application/json")

        try:
            deleted = await self._delete(data)
            res = WebResponse(
                status=Status2.success if deleted else Status2.error,
                status_code=200 if deleted else 400,
                message="Successfully deleted data."
                if deleted
                else "Unable to delete data.",
                reason=None,
            )
        except KeyError as exc:
            log.error(exc, exc_info=True)
            res = WebResponse(
                status=Status2.error,
                status_code=400,
                reason=None,
                message="Unable to delete data",
                errors=[f"Unable to find {self._config_key}"],
            )
            return self.finish()

        self.set_status(res.status_code)
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return deleted


class MultiItemsDDBConfigurationCrudHandler(BaseConfigurationCrudHandler):
    """
    Handler class to manage CRUD operations for multiple items on a DynamoDB configuration.

    Required Fields:
        _model_class: The pydantic model class to use for validate the request.
        _config_key: The key in the configuration that contains the list of items to be operated on.
        _request_list_key: The key in the request body that contains the list of items to be operated on.
    """

    _request_list_key: str

    async def _validate_body(self, items: list):
        """Validate the body of a request. Can be overridden to add custom validation logic.

        Args:
            items (list): The items to validate.

        Returns:
            bool: True by default, or can be overridden to raise on validation failure.
        """
        return True

    async def _validate_delete(self, **kwargs):
        """Validate a delete request. Can be overridden to add custom validation logic.

        Returns:
            bool: True by default, or can be overridden to raise on validation failure.
        """
        return True

    async def _get_body_data(self):
        """Retrieve and validates the data from the request body.

        Returns:
            list: A list of items extracted from the request body.
        """

        data = tornado.escape.json_decode(self.request.body)
        # TODO: use self._model_class to validate the body if it exists
        items: list[str] = data.get(self._request_list_key)
        await self._validate_body(items)
        return items

    async def _retrieve(self) -> list:
        """Retrieve the current list from DDB.

        Returns:
            list: A list of current configuration items.
        """

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )
        current: list[str] = list(get_in(dynamic_config, self._config_key))  # type: ignore
        return current

    async def _create(self, data):
        raise NotImplementedError

    async def _update(self, items: list[str]):
        """Update the current configuration with new items.

        Args:
            items (list[str]): The new items to add to the configuration.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        current: list[str] = await self._retrieve()

        set_in(dynamic_config, self._config_key, list(set([*current, *items])))

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config),
            self.user,
            self.ctx.tenant,
        )

        return True

    async def _delete(self, items: list[str]):
        """Delete specified items from the current configuration.

        Args:
            items (list[str]): The items to delete from the configuration.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        current: list[str] = await self._retrieve()
        difference = list(set(current).difference(items))

        await self._validate_delete(
            current=current,
            difference=difference,
            items=items,
        )

        set_in(dynamic_config, self._config_key, difference)

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config),
            self.user,
            self.ctx.tenant,
        )

        return True
