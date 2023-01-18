from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus
from io import BytesIO

import pytest
from werkzeug.exceptions import UnsupportedMediaType
from werkzeug.wrappers import Request

from rouver.args import Multiplicity
from rouver.handler import RouteHandlerBase
from rouver_test.testutil import StubStartResponse, default_environment


class StubHandler(RouteHandlerBase):
    response: Iterable[bytes] = []

    def prepare_response(self) -> Iterable[bytes]:
        self.respond()
        return self.response


class TestRouteHandlerBase:
    @pytest.fixture(autouse=True)
    def setup_environment(self) -> None:
        self.environ = default_environment()
        self.start_response = StubStartResponse()

    def call_handler(self, handler_class: type[RouteHandlerBase]) -> bytes:
        handler = handler_class(self.environ, self.start_response)
        response = b"".join(handler)
        handler.close()
        return response

    def test_attributes(self) -> None:
        handler = StubHandler(self.environ, self.start_response)
        assert handler.request.environ is self.environ
        assert isinstance(handler.request, Request)
        assert handler.start_response is self.start_response

    def test_path_args__from_environment(self) -> None:
        self.environ["rouver.path_args"] = ["foo"]
        handler = StubHandler(self.environ, self.start_response)
        assert handler.path_args == ["foo"]

    def test_path_args__default(self) -> None:
        handler = StubHandler(self.environ, self.start_response)
        assert handler.path_args == []

    def test_path_args__not_a_list(self) -> None:
        self.environ["rouver.path_args"] = "not-a-list"
        handler = StubHandler(self.environ, self.start_response)
        assert handler.path_args == []

    def test_wildcard_path__from_environment(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo/bar"
        handler = StubHandler(self.environ, self.start_response)
        assert handler.wildcard_path == "/foo/bar"

    def test_wildcard_path__decode(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo%2Fb%C3%A4r"
        handler = StubHandler(self.environ, self.start_response)
        assert handler.wildcard_path == "/foo/bär"

    def test_wildcard_path__decode_errors(self) -> None:
        self.environ["rouver.wildcard_path"] = "/foo%2Fb%C3r"
        handler = StubHandler(self.environ, self.start_response)
        assert handler.wildcard_path == "/foo/b�r"

    def test_wildcard_path__default(self) -> None:
        handler = StubHandler(self.environ, self.start_response)
        assert handler.wildcard_path == ""

    def test_wildcard_path__not_a_string(self) -> None:
        self.environ["rouver.wildcard_path"] = b"not-a-str"
        handler = StubHandler(self.environ, self.start_response)
        assert handler.wildcard_path == ""

    def test_parse_args__post_twice(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"foo=bar&abc=def")
        self.environ["REQUEST_METHOD"] = "POST"
        self.environ["CONTENT_LENGTH"] = "15"
        self.environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        handler = StubHandler(self.environ, self.start_response)
        args1 = handler.parse_args([("foo", str, Multiplicity.REQUIRED)])
        assert args1 == {"foo": "bar"}
        args2 = handler.parse_args(
            [
                ("foo", str, Multiplicity.REQUIRED),
                ("abc", str, Multiplicity.REQUIRED),
            ]
        )
        assert args2 == {"foo": "bar", "abc": "def"}

    def test_parse_args__works_in_response_handler(self) -> None:
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

    def test_parse_json_request__default_encoding(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b'{ "f\xc3\xb6o": 42 }')
        self.environ["CONTENT_LENGTH"] = "14"
        self.environ["CONTENT_TYPE"] = "application/json"
        handler = StubHandler(self.environ, self.start_response)
        j = handler.parse_json_request()
        assert j == {"föo": 42}

    def test_parse_json_request__explicit_encoding(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b'{ "f\xf6o": 42 }')
        self.environ["CONTENT_LENGTH"] = "13"
        self.environ["CONTENT_TYPE"] = "application/json; charset=iso-8859-1"
        handler = StubHandler(self.environ, self.start_response)
        j = handler.parse_json_request()
        assert j == {"föo": 42}

    def test_parse_json_request__unknown_encoding(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"{}")
        self.environ["CONTENT_LENGTH"] = "2"
        self.environ["CONTENT_TYPE"] = "application/json; charset=unknown"
        handler = StubHandler(self.environ, self.start_response)
        with pytest.raises(UnsupportedMediaType):
            handler.parse_json_request()

    def test_parse_json_request__no_content_type(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"{}")
        self.environ["CONTENT_LENGTH"] = "2"
        handler = StubHandler(self.environ, self.start_response)
        with pytest.raises(UnsupportedMediaType):
            handler.parse_json_request()

    def test_parse_json_request__wrong_content_type(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"{}")
        self.environ["CONTENT_LENGTH"] = "2"
        self.environ["CONTENT_TYPE"] = "application/octet-stream"
        handler = StubHandler(self.environ, self.start_response)
        with pytest.raises(UnsupportedMediaType):
            handler.parse_json_request()

    def test_parse_json_request__invalid_data(self) -> None:
        self.environ["wsgi.input"] = BytesIO(b"INVALID")
        self.environ["CONTENT_LENGTH"] = "7"
        self.environ["CONTENT_TYPE"] = "application/json"
        handler = StubHandler(self.environ, self.start_response)
        with pytest.raises(UnsupportedMediaType):
            handler.parse_json_request()

    def test_respond(self) -> None:
        StubHandler.response = [b"foo", b"bar"]
        response = self.call_handler(StubHandler)
        self.start_response.assert_status(HTTPStatus.OK)
        assert response == b"foobar"

    def test_closeable_response(self) -> None:
        StubHandler.response = BytesIO(b"foo")
        response = self.call_handler(StubHandler)
        self.start_response.assert_status(HTTPStatus.OK)
        assert response == b"foo"
        assert StubHandler.response.closed
