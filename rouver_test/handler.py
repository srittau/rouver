from http import HTTPStatus
from typing import Type, Iterator
from unittest import TestCase

from asserts import assert_is, assert_equal
from werkzeug.wrappers import Request

from rouver.handler import RouteHandlerBase

from rouver_test.util import default_environment, TestingStartResponse


class RouteHandlerBaseTest(TestCase):

    def setUp(self) -> None:
        self.request = Request(default_environment())
        self.start_response = TestingStartResponse()

    def call_handler(self, handler_class: Type[RouteHandlerBase]) -> bytes:
        handler = handler_class(self.request, [], self.start_response)
        return b"".join(handler)

    def test_attributes(self) -> None:
        handler = RouteHandlerBase(self.request, ["foo"], self.start_response)
        assert_is(self.request, handler.request)
        assert_equal(["foo"], handler.path_args)
        assert_is(self.start_response, handler.start_response)

    def test_respond(self) -> None:
        class TestingHandler(RouteHandlerBase):
            def __iter__(self) -> Iterator[bytes]:
                return self.respond()
        response = self.call_handler(TestingHandler)
        self.start_response.assert_status(HTTPStatus.OK)
        assert_equal(b"", response)
