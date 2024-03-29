"""Docstring in public module."""

# import unittest
import os
import sys

import mock
import pytest
from mock import Mock, patch
from tornado.httpclient import AsyncHTTPClient

# from tornado.options import options
from tornado.testing import AsyncHTTPTestCase

from util.tests.fixtures.util import NOQAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


@pytest.mark.usefixtures("aws_credentials")
class TestMain(NOQAsyncHTTPTestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestMain, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)

    def get_app(self):
        from api import __main__

        self.__main__ = __main__
        app = self.__main__.main()
        return app

    @patch("api.__main__.asyncio.get_event_loop")
    def broken_test_main(self, mock_ioloop):
        """Docstring in public method."""
        self.__main__.app = Mock()
        self.__main__.app.listen = Mock()
        with patch.object(self.__main__, "main", return_value=42):
            with patch.object(self.__main__, "__name__", "__main__"):
                self.__main__.config = {}
                mock_ioloop.run_forever = mock.Mock()
                mock_ioloop.add_handler = mock.Mock()
                mock_ioloop.start = mock.Mock()
                self.__main__.init()


@pytest.mark.usefixtures("aws_credentials")
@pytest.mark.usefixtures("dynamodb")
class TestHealth(AsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_health(self):
        """Docstring in public method."""
        response = self.fetch("/healthcheck", method="GET", follow_redirects=False)
        self.assertEqual(b"OK", response.body)
