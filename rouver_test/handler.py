from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus
from io import BytesIO

from asserts import assert_equal, assert_is, assert_is_instance, assert_raises
from dectest import TestCase, before, test
from werkzeug.exceptions import UnsupportedMediaType
from werkzeug.wrappers import Request

from rouver.args import Multiplicity
from rouver.handler import RouteHandlerBase
from rouver_test.testutil import TestingStartResponse, default_environment


class TestingHandler(RouteHandlerBase):
    response: Iterable[bytes] = []

    def prepare_response(self) -> Iterable[bytes]:
        self.respond()
        return self.response


class RouteHandlerBaseTest(TestCase):
    @before
    def setup_environment(self) -> None:
        self.environ = default_environment()
        self.start_response = TestingStartResponse()

    def call_handler(self, handler_class: type[RouteHandlerBase]) -> bytes:
        handler = handler_class(self.environ, self.start_response)
        return b"".join(handler)

    @test
    def attributes(self) -> None:
        handler = TestingHandler(self.environ, self.start_response)
        assert_is(self.environ, handler.request.environ)
        assert_is_instance(handler.request, Request)
        assert_is(self.start_response, handler.start_response)

    @test
    def path_args__from_environment(self) -> None:
        self.environ["rouver.path_args"] = ["foo"]
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal(["foo"], handler.path_args)

    @test
    def path_args__default(self) -> None:
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal([], handler.path_args)

    @test
    def path_args__not_a_list(self) -> None:
        self.environ["rouver.path_args"] = "not-a-list"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal([], handler.path_args)

    @test
    def wildcard_path__from_environment(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo/bar"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("/foo/bar", handler.wildcard_path)

    @test
    def wildcard_path__decode(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo%2Fb%C3%A4r"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("/foo/bär", handler.wildcard_path)

    @test
    def wildcard_path__decode_errors(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo%2Fb%C3r"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("/foo/b�r", handler.wildcard_path)

    @test
    def wildcard_path__default(self) -> None:
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("", handler.wildcard_path)

    @test
    def wildcard_path__not_a_string(self) -> None:
        self.environ["rouver.wildcard_path"] = b"not-a-str"
        handler = TestingHandler(self.environ, self.start_response)
        assert_equal("", handler.wildcard_path)

    @test
    def parse_args__post_twice(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"foo=bar&abc=def")
        self.environ["REQUEST_METHOD"] = "POST"
        self.environ["CONTENT_LENGTH"] = "15"
        self.environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        handler = TestingHandler(self.environ, self.start_response)
        args1 = handler.parse_args([("foo", str, Multiplicity.REQUIRED)])
        assert_equal({"foo": "bar"}, args1)
        args2 = handler.parse_args(
            [
                ("foo", str, Multiplicity.REQUIRED),
                ("abc", str, Multiplicity.REQUIRED),
            ]
        )
        assert_equal({"foo": "bar", "abc": "def"}, args2)

    @test
    def parse_args__works_in_response_handler(self) -> None:
        class MyHandler(RouteHandlerBase):
            def prepare_response(self) -> Iterable[bytes]:
                self.parse_args([])
                return self.respond()

        self.environ["wsgi.input"] = BytesIO(b"foo=bar&abc=def")
        self.environ["REQUEST_METHOD"] = "POST"
        self.environ["CONTENT_LENGTH"] = "15"
        self.environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        handler = MyHandler(self.environ, self.start_response)
        iter(handler)

    @test
    def parse_json_request__default_encoding(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b'{ "f\xc3\xb6o": 42 }')
        self.environ["CONTENT_LENGTH"] = "14"
        self.environ["CONTENT_TYPE"] = "application/json"
        handler = TestingHandler(self.environ, self.start_response)
        j = handler.parse_json_request()
        assert_equal({"föo": 42}, j)

    @test
    def parse_json_request__explicit_encoding(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b'{ "f\xf6o": 42 }')
        self.environ["CONTENT_LENGTH"] = "13"
        self.environ["CONTENT_TYPE"] = "application/json; charset=iso-8859-1"
        handler = TestingHandler(self.environ, self.start_response)
        j = handler.parse_json_request()
        assert_equal({"föo": 42}, j)

    @test
    def parse_json_request__unknown_encoding(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"{}")
        self.environ["CONTENT_LENGTH"] = "2"
        self.environ["CONTENT_TYPE"] = "application/json; charset=unknown"
        handler = TestingHandler(self.environ, self.start_response)
        with assert_raises(UnsupportedMediaType):
            handler.parse_json_request()

    @test
    def parse_json_request__no_content_type(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"{}")
        self.environ["CONTENT_LENGTH"] = "2"
        handler = TestingHandler(self.environ, self.start_response)
        with assert_raises(UnsupportedMediaType):
            handler.parse_json_request()

    @test
    def parse_json_request__wrong_content_type(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"{}")
        self.environ["CONTENT_LENGTH"] = "2"
        self.environ["CONTENT_TYPE"] = "application/octet-stream"
        handler = TestingHandler(self.environ, self.start_response)
        with assert_raises(UnsupportedMediaType):
            handler.parse_json_request()

    @test
    def parse_json_request__invalid_data(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"INVALID")
        self.environ["CONTENT_LENGTH"] = "7"
        self.environ["CONTENT_TYPE"] = "application/json"
        handler = TestingHandler(self.environ, self.start_response)
        with assert_raises(UnsupportedMediaType):
            handler.parse_json_request()

    @test
    def respond(self) -> None:
        TestingHandler.response = [b"foo", b"bar"]
        response = self.call_handler(TestingHandler)
        self.start_response.assert_status(HTTPStatus.OK)
        assert_equal(b"foobar", response)
