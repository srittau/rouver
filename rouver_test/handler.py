from http import HTTPStatus
from typing import Type, Iterable
from unittest import TestCase

from asserts import assert_is, assert_equal, assert_is_instance

from werkzeug.wrappers import Request

from rouver.handler import RouteHandlerBase

from rouver_test.util import default_environment, TestingStartResponse


class TestingHandler(RouteHandlerBase):

    response = []  # type: Iterable[bytes]

    def prepare_response(self) -> Iterable[bytes]:
        self.respond()
        return self.response


class RouteHandlerBaseTest(TestCase):

    def setUp(self) -> None:
        self.environ = default_environment()
        self.start_response = TestingStartResponse()

    def call_handler(self, handler_class: Type[RouteHandlerBase]) -> bytes:
        handler = handler_class(self.environ, self.start_response)
        return b"".join(handler)

    def test_attributes(self) -> None:
        handler = TestingHandler(self.environ, self.start_response)
        assert_is(self.environ, handler.request.environ)
        assert_is_instance(handler.request, Request)
        assert_is(self.start_response, handler.start_response)

    def test_path_args__from_environment(self) -> None:
        self.environ["rouver.path_args"] = ["foo"]
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal(["foo"], handler.path_args)

    def test_path_args__default(self) -> None:
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal([], handler.path_args)

    def test_path_args__not_a_list(self) -> None:
        self.environ["rouver.path_args"] = "not-a-list"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal([], handler.path_args)

    def test_wildcard_path__from_environment(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo/bar"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("/foo/bar", handler.wildcard_path)

    def test_wildcard_path__decode(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo%2Fb%C3%A4r"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("/foo/bär", handler.wildcard_path)

    def test_wildcard_path__decode_errors(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo%2Fb%C3r"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("/foo/b�r", handler.wildcard_path)

    def test_wildcard_path__default(self) -> None:
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("", handler.wildcard_path)

    def test_wildcard_path__not_a_string(self) -> None:
        self.environ["rouver.wildcard_path"] = b"not-a-str"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("", handler.wildcard_path)

    def test_respond(self) -> None:
        TestingHandler.response = [b"foo", b"bar"]
        response = self.call_handler(TestingHandler)
        self.start_response.assert_status(HTTPStatus.OK)
        assert_equal(b"foobar", response)
