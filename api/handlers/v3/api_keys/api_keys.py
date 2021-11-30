import tornado.escape

from common.handlers.base import BaseHandler
from common.lib.dynamo import UserDynamoHandler
from common.models import Status2, WebResponse


class AddApiKeyHandler(BaseHandler):
    async def post(self):
        """
        Add API key
        """
        self.set_header("Content-Type", "application/json")
        self.set_status(200)
        self.write({"message": "OK"})
        host = self.ctx.host
        ddb = UserDynamoHandler(host, user=self.user)
        api_key = ddb.create_api_key(self.user, host)
        self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                data={"api_key": api_key},
            ).json(exclude_unset=True)
        )

    async def delete(self):
        """
        Delete API key
        """
        data = tornado.escape.json_decode(self.request.body)
        api_key = data.get("api_key")
        api_key_id = data.get("api_key_id")
        if not api_key and not api_key_id:
            raise ValueError("api_key or api_key_id is required")
        host = self.ctx.host
        ddb = UserDynamoHandler(host, user=self.user)
        await ddb.delete_api_key(
            host, self.user, api_key=api_key, api_key_id=api_key_id
        )
        self.set_header("Content-Type", "application/json")
        self.set_status(200)
        self.write({"message": "OK"})

    async def get(self):
        """
        Get API keys
        """
        self.set_header("Content-Type", "application/json")
        self.set_status(200)
        self.write({"message": "OK"})

    async def put(self):
        """
        Update API key
        """
        raise NotImplementedError
