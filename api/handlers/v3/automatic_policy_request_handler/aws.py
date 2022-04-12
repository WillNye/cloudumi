import tornado.escape

from common.handlers.base import BaseHandler


class AutomaticPolicyRequestHandler(BaseHandler):
    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        print(data)
