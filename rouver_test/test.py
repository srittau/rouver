from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from http import HTTPStatus
from io import BytesIO
from typing import Any

import pytest
from werkzeug.formparser import parse_form_data

from rouver.args import ArgumentTemplate, Multiplicity, parse_args
from rouver.exceptions import ArgumentsError
from rouver.test import (
    ArgumentToTest,
    FakeRequest,
    FakeResponse,
    create_request,
    run_wsgi_test,
    test_wsgi_arguments as run_wsgi_arguments_test,
)
from rouver.types import StartResponse, WSGIApplication, WSGIEnvironment


def assert_wsgi_input_stream(stream: object) -> None:
    assert hasattr(stream, "read")
    assert hasattr(stream, "readline")
    assert hasattr(stream, "readlines")
    assert hasattr(stream, "__iter__")


class TestRequestTest:
    def test_attributes(self) -> None:
        request = create_request("GET", "/foo/bar")
        assert request.method == "GET"
        assert request.path == "/foo/bar"
        assert request.content_type is None
        assert isinstance(request.error_stream, BytesIO)

    def test_capitalize_method(self) -> None:
        request = create_request("pOst", "/foo/bar")
        assert request.method == "POST"

    def test_to_environment__minimal(self) -> None:
        request = create_request("GET", "/foo/bar")
        environ = request.to_environment()
        assert {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/foo/bar",
            "SERVER_NAME": "www.example.com",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "REMOTE_ADDR": "127.0.0.1",
            "SCRIPT_NAME": "",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": True,
            "wsgi.errors": request.error_stream,
        }.items() <= environ.items()
        assert_wsgi_input_stream(environ["wsgi.input"])
        assert environ["wsgi.input"].read() == b""
        assert "CONTENT_TYPE" not in environ
        assert "CONTENT_LENGTH" not in environ
        assert "QUERY_STRING" not in environ

    def test_to_environment__post(self) -> None:
        request = create_request("POST", "/foo/bar")
        environ = request.to_environment()
        assert {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/foo/bar",
            "SCRIPT_NAME": "",
            "SERVER_NAME": "www.example.com",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "REMOTE_ADDR": "127.0.0.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": True,
            "wsgi.errors": request.error_stream,
        }.items() <= environ.items()
        assert_wsgi_input_stream(environ["wsgi.input"])
        assert environ["wsgi.input"].read() == b""
        assert "CONTENT_TYPE" not in environ
        assert "CONTENT_LENGTH" not in environ
        assert "QUERY_STRING" not in environ

    def test_to_environment__post_urlencoded(self) -> None:
        request = create_request("POST", "/foo/bar")
        request.add_argument("arg", "value")
        environ = request.to_environment()
        assert {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "CONTENT_LENGTH": "9",
        }.items() <= environ.items()
        assert_wsgi_input_stream(environ["wsgi.input"])
        assert environ["wsgi.input"].read() == b"arg=value"
        assert "QUERY_STRING" not in environ

    def test__explicit_script_name(self) -> None:
        request = create_request("GET", "/baz/bar")
        assert request.full_path == "/baz/bar"
        request.script_name = "/foo"
        assert request.full_path == "/foo/baz/bar"
        assert {
            "SCRIPT_NAME": "/foo",
            "PATH_INFO": "/baz/bar",
        }.items() <= request.to_environment().items()

    def test_set_env_var(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_env_var("foo.bar", "baz")
        environ = request.to_environment()
        assert environ["foo.bar"] == "baz"

    def test_set_env_var__priority(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_env_var("SERVER_PORT", "8888")
        request.set_env_var("HTTP_X_FOO", "Set by env var")
        request.set_header("X-Foo", "Set by header")
        environ = request.to_environment()
        assert environ["SERVER_PORT"] == "8888"
        assert environ["HTTP_X_FOO"] == "Set by env var"

    def test_set_header(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_header("X-Foobar", "Baz")
        environ = request.to_environment()
        assert environ["HTTP_X_FOOBAR"] == "Baz"

    def test_set_header__content_type(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_header("Content-Type", "text/html")
        assert request.content_type == "text/html"
        environ = request.to_environment()
        assert environ["CONTENT_TYPE"] == "text/html"
        assert "HTTP_CONTENT_TYPE" not in environ

    def test_add_argument__content_type(self) -> None:
        request = create_request("POST", "/foo/bar")
        assert request.content_type is None
        request.add_argument("foo", "bar")
        assert request.content_type is None
        environ = request.to_environment()
        assert environ["CONTENT_TYPE"] == "application/x-www-form-urlencoded"

        request = create_request("POST", "/foo/bar")
        request.content_type = "image/png"
        request.add_argument("abc", "def")
        assert request.content_type == "image/png"
        environ = request.to_environment()
        assert environ["CONTENT_TYPE"] == "image/png"

        request = create_request("GET", "/foo/bar")
        assert request.content_type is None
        request.add_argument("foo", "bar")
        assert request.content_type is None
        environ = request.to_environment()
        assert "CONTENT_TYPE" not in environ

    def test_add_file_argument__content_type(self) -> None:
        request = create_request("POST", "/foo/bar")
        assert request.content_type is None
        request.add_file_argument("foo", b"", "text/plain")
        assert request.content_type is None
        environ = request.to_environment()
        content_type, boundary = environ["CONTENT_TYPE"].split(";")
        assert content_type == "multipart/form-data"

        request = create_request("POST", "/foo/bar")
        request.content_type = "image/png"
        request.add_file_argument("abc", b"", "text/plain")
        assert request.content_type == "image/png"
        environ = request.to_environment()
        assert environ["CONTENT_TYPE"] == "image/png"

    def test_add_argument__body_set(self) -> None:
        put_request = create_request("PUT", "/foo")
        put_request.body = b"Body"
        with pytest.raises(ValueError):
            put_request.add_argument("foo", "bar")

    def test_add_file_argument__body_set(self) -> None:
        put_request = create_request("PUT", "/foo")
        put_request.body = b"Body"
        with pytest.raises(ValueError):
            put_request.add_file_argument("foo", b"", "text/plain")

    def test_add_file_argument__unsupported_method(self) -> None:
        get_request = create_request("GET", "/foo")
        with pytest.raises(ValueError):
            get_request.add_file_argument("foo", b"", "text/plain")

    def test_to_environment__content_type(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.content_type = "image/png"
        environ = request.to_environment()
        assert environ["CONTENT_TYPE"] == "image/png"

    def test_arguments__get_request(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("foo", "bar")
        request.add_argument("abc", ["def", "ghi"])
        environ = request.to_environment()
        assert environ["QUERY_STRING"] == "foo=bar&abc=def&abc=ghi"

    def test_arguments__put_request(self) -> None:
        request = create_request("PUT", "/foo")
        request.add_argument("foo", "bar")
        request.add_argument("abc", ["def", "ghi"])
        environ = request.to_environment()
        assert "QUERY_STRING" not in environ
        assert environ["CONTENT_TYPE"] == "application/x-www-form-urlencoded"
        assert environ["wsgi.input"].read() == b"foo=bar&abc=def&abc=ghi"

    def test_arguments__quote(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("föo", "bär")
        environ = request.to_environment()
        assert environ["QUERY_STRING"] == "f%C3%B6o=b%C3%A4r"

    def test_file_arguments(self) -> None:
        request = create_request("PUT", "/foo")
        request.add_argument("foo", "bar")
        request.add_file_argument("file1", b"content1", "text/plain")
        request.add_file_argument(
            "file2", b"content2", "image/png", filename="foobar"
        )
        environ = request.to_environment()
        assert "QUERY_STRING" not in environ
        content_type, boundary = environ["CONTENT_TYPE"].split(";")
        assert content_type == "multipart/form-data"
        _, args, files = parse_form_data(environ)
        assert len(args) == 1
        assert "bar" == args["foo"]
        assert len(files) == 2
        file1 = files["file1"]
        assert file1.mimetype == "text/plain"
        assert file1.filename == ""
        assert file1.stream.read() == b"content1"
        file2 = files["file2"]
        assert file2.mimetype == "image/png"
        assert file2.filename == "foobar"
        assert file2.stream.read() == b"content2"

    def test_file_arguments__umlauts(self) -> None:
        request = create_request("PUT", "/foo")
        request.add_argument('f"öo', "bär")
        request.add_file_argument(
            'f"öle', b"", "text/plain", filename="ä\"'bc"
        )
        environ = request.to_environment()
        assert "QUERY_STRING" not in environ
        content_type, _ = environ["CONTENT_TYPE"].split(";")
        assert content_type == "multipart/form-data"
        _, args, files = parse_form_data(environ)
        assert len(args) == 1
        assert "bär" == args['f"%C3%B6o']
        assert len(files) == 1
        file = files['f"%C3%B6le']
        assert file.mimetype == "text/plain"
        assert file.filename == "ä\"'bc"
        assert file.stream.read() == b""

    def test_clear_arguments(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("foo", "bar")
        request.clear_arguments()
        environ = request.to_environment()
        assert "QUERY_STRING" not in environ

        request = create_request("POST", "/foo")
        request.add_argument("foo", "bar")
        request.clear_arguments()
        environ = request.to_environment()
        content = environ["wsgi.input"].read()
        assert content == b""

    def test_body(self) -> None:
        request = create_request("POST", "/")
        assert request.body == b""
        request.body = b"Test Body"
        assert request.body == b"Test Body"
        environ = request.to_environment()
        assert environ.get("CONTENT_LENGTH") == "9"
        assert environ["wsgi.input"].read() == b"Test Body"

    def test_set_body_in_get_request(self) -> None:
        request = create_request("GET", "/")
        request.body = b""
        with pytest.raises(ValueError):
            request.body = b"Test Body"

    def test_set_body_when_argument_is_set(self) -> None:
        request = create_request("POST", "/")
        request.add_argument("foo", "bar")
        with pytest.raises(ValueError):
            request.body = b""
        with pytest.raises(ValueError):
            request.body = b"Body"

    def _assert_json_request(
        self, request: FakeRequest, expected_body: bytes
    ) -> None:
        assert request.body == expected_body
        env = request.to_environment()
        assert env["CONTENT_LENGTH"] == str(len(expected_body))
        assert env["CONTENT_TYPE"] == "application/json; charset=utf-8"
        assert env["wsgi.input"].read() == expected_body

    def test_set_json_request__get_request(self) -> None:
        request = create_request("GET", "/")
        with pytest.raises(ValueError):
            request.set_json_request(b"{}")

    def test_set_json_request__bytes(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request(b"{}")
        self._assert_json_request(request, b"{}")

    def test_set_json_request__str(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request('{"foo": "bär"}')
        self._assert_json_request(request, '{"foo": "bär"}'.encode("utf-8"))

    def test_set_json_request__dict(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request({"foo": "bär"})
        self._assert_json_request(request, b'{"foo": "b\\u00e4r"}')

    def test_set_json_request__list(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request(["foo", "bär"])
        self._assert_json_request(request, b'["foo", "b\\u00e4r"]')


class TestFakeResponse:
    def test_attributes(self) -> None:
        response = FakeResponse("200 OK", [])
        assert response.status_line == "200 OK"
        assert response.status == HTTPStatus.OK
        assert response.body == b""

    def test_unknown_status(self) -> None:
        with pytest.raises(ValueError):
            FakeResponse("999 Unknown", [])

    def test_invalid_status_line(self) -> None:
        with pytest.raises(ValueError):
            FakeResponse("INVALID", [])

    def test_get_header_value(self) -> None:
        response = FakeResponse(
            "200 OK",
            [
                ("X-Header", "Foobar"),
                ("Content-Type", "image/png"),
                ("Allow", "GET"),
            ],
        )
        assert response.get_header_value("Content-Type") == "image/png"
        assert response.get_header_value("content-TYPE") == "image/png"
        with pytest.raises(ValueError):
            response.get_header_value("X-Unknown")

    def test_parse_json_body(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "application/json")]
        )
        response.body = b'{"foo": 5}'
        json = response.parse_json_body()
        assert json == {"foo": 5}

    def test_parse_json_body__wrong_content_type(self) -> None:
        response = FakeResponse("200 OK", [("Content-Type", "text/plain")])
        response.body = b"{}"
        with pytest.raises(AssertionError):
            response.parse_json_body()

    def test_parse_json_body__wrong_content_encoding(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "application/json; charset=latin1")]
        )
        response.body = b"{}"
        with pytest.raises(AssertionError):
            response.parse_json_body()

    def test_parse_json_body__invalid_json(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "application/json")]
        )
        response.body = b'{"foo":'
        with pytest.raises(AssertionError):
            response.parse_json_body()

    def test_parse_json_body__invalid_encoding(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "application/json; charset=utf-8")]
        )
        response.body = '{"föo": 5}'.encode("iso-8859-1")
        with pytest.raises(AssertionError):
            response.parse_json_body()

    def test_assert_status__ok(self) -> None:
        response = FakeResponse("404 Not Found", [])
        response.assert_status(HTTPStatus.NOT_FOUND)

    def test_assert_status__fail(self) -> None:
        response = FakeResponse("404 Not Found", [])
        with pytest.raises(AssertionError):
            response.assert_status(HTTPStatus.OK)

    def test_assert_header_not_set__is_set(self) -> None:
        response = FakeResponse("200 OK", [("X-Foo", "value")])
        with pytest.raises(AssertionError):
            response.assert_header_not_set("x-FOO")

    def test_assert_header_not_set__not_set(self) -> None:
        response = FakeResponse("200 OK", [])
        response.assert_header_not_set("X-Foo")

    def test_assert_header_equal__no_such_header(self) -> None:
        response = FakeResponse("200 OK", [("X-Other", "value")])
        with pytest.raises(AssertionError):
            response.assert_header_equal("X-Header", "value")

    def test_assert_header_equal__ok(self) -> None:
        response = FakeResponse("200 OK", [("X-Header", "value")])
        response.assert_header_equal("X-Header", "value")

    def test_assert_header_equal__differs(self) -> None:
        response = FakeResponse("200 OK", [("X-Header", "other")])
        with pytest.raises(AssertionError):
            response.assert_header_equal("X-Header", "value")

    def test_assert_created_at__ok(self) -> None:
        response = FakeResponse(
            "201 Created", [("Location", "http://example.com/")]
        )
        response.assert_created_at("http://example.com/")

    def test_assert_created_at__wrong_status(self) -> None:
        response = FakeResponse(
            "200 OK", [("Location", "http://example.com/")]
        )
        with pytest.raises(AssertionError):
            response.assert_created_at("http://example.com/")

    def test_assert_created_at__no_location_header(self) -> None:
        response = FakeResponse("201 Created", [])
        with pytest.raises(AssertionError):
            response.assert_created_at("http://example.org/")

    def test_assert_created_at__wrong_location(self) -> None:
        response = FakeResponse(
            "201 Created", [("Location", "http://example.com/")]
        )
        with pytest.raises(AssertionError):
            response.assert_created_at("http://example.org/")

    def test_assert_created_at__relative_location(self) -> None:
        response = FakeResponse(
            "201 Created", [("Location", "http://example.com/foo/bar")]
        )
        response.assert_created_at("/foo/bar")

    def test_assert_created_at__keep_query_string(self) -> None:
        response = FakeResponse(
            "201 Created",
            [("Location", "http://example.com/foo?abc=def#frag")],
        )
        response.assert_created_at("/foo?abc=def#frag")

    def test_assert_see_other__ok(self) -> None:
        response = FakeResponse(
            "303 See Other", [("Location", "http://example.com/")]
        )
        response.assert_see_other("http://example.com/")

    def test_assert_see_other__wrong_status(self) -> None:
        response = FakeResponse(
            "200 OK", [("Location", "http://example.com/")]
        )
        with pytest.raises(AssertionError):
            response.assert_see_other("http://example.com/")

    def test_assert_see_other__no_location_header(self) -> None:
        response = FakeResponse("303 See Other", [])
        with pytest.raises(AssertionError):
            response.assert_see_other("http://example.org/")

    def test_assert_see_other__wrong_location(self) -> None:
        response = FakeResponse(
            "303 See Other", [("Location", "http://example.com/")]
        )
        with pytest.raises(AssertionError):
            response.assert_see_other("http://example.org/")

    def test_assert_see_other__relative_location(self) -> None:
        response = FakeResponse(
            "303 See Other", [("Location", "http://example.com/foo/bar")]
        )
        response.assert_see_other("/foo/bar")

    def test_assert_see_other__keep_query_string(self) -> None:
        response = FakeResponse(
            "303 See Other",
            [("Location", "http://example.com/foo?abc=def#frag")],
        )
        response.assert_see_other("/foo?abc=def#frag")

    def test_assert_temporary_redirect__ok(self) -> None:
        response = FakeResponse(
            "307 Temporary Redirect", [("Location", "http://example.com/")]
        )
        response.assert_temporary_redirect("http://example.com/")

    def test_assert_temporary_redirect__wrong_status(self) -> None:
        response = FakeResponse(
            "200 OK", [("Location", "http://example.com/")]
        )
        with pytest.raises(AssertionError):
            response.assert_temporary_redirect("http://example.com/")

    def test_assert_temporary_redirect__no_location_header(self) -> None:
        response = FakeResponse("307 Temporary Redirect", [])
        with pytest.raises(AssertionError):
            response.assert_temporary_redirect("http://example.org/")

    def test_assert_temporary_redirect__wrong_location(self) -> None:
        response = FakeResponse(
            "307 Temporary Redirect", [("Location", "http://example.com/")]
        )
        with pytest.raises(AssertionError):
            response.assert_temporary_redirect("http://example.org/")

    def test_assert_temporary_redirect__relative_location(self) -> None:
        response = FakeResponse(
            "307 Temporary Redirect",
            [("Location", "http://example.com/foo/bar")],
        )
        response.assert_temporary_redirect("/foo/bar")

    def test_assert_temporary_redirect__keep_query_string(self) -> None:
        response = FakeResponse(
            "307 Temporary Redirect",
            [("Location", "http://example.com/foo?abc=def#frag")],
        )
        response.assert_temporary_redirect("/foo?abc=def#frag")

    def test_assert_content_type__no_such_header(self) -> None:
        response = FakeResponse("200 OK", [])
        with pytest.raises(AssertionError):
            response.assert_content_type("image/png")

    def test_assert_content_type__equal(self) -> None:
        response = FakeResponse("200 OK", [("Content-Type", "image/png")])
        response.assert_content_type("image/png")

    def test_assert_content_type__different(self) -> None:
        response = FakeResponse("200 OK", [("Content-Type", "image/png")])
        with pytest.raises(AssertionError):
            response.assert_content_type("image/jpeg")

    def test_assert_content_type__charset_matches(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "text/html; charset=us-ascii")]
        )
        response.assert_content_type("text/html", charset="us-ascii")

    def test_assert_content_type__charset_list_matches(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "text/html; charset=us-ascii")]
        )
        response.assert_content_type(
            "text/html", charset=["us-ascii", "utf-8", None]
        )

    def test_assert_content_type__charset_list_matches__none(self) -> None:
        response = FakeResponse("200 OK", [("Content-Type", "text/html")])
        response.assert_content_type(
            "text/html", charset=["us-ascii", "utf-8", None]
        )

    def test_assert_content_type__charset_not_checked(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "text/html; charset=utf-8")]
        )
        response.assert_content_type("text/html")

    def test_assert_content_type__no_charset_in_response(self) -> None:
        response = FakeResponse("200 OK", [("Content-Type", "text/html")])
        with pytest.raises(AssertionError):
            response.assert_content_type("text/html", charset="us-ascii")

    def test_assert_content_type__wrong_charset(self) -> None:
        response = FakeResponse(
            "200 OK", [("Content-Type", "text/html; charset=utf-8")]
        )
        with pytest.raises(AssertionError):
            response.assert_content_type("text/html", charset="us-ascii")

    def test_assert_set_cookie__simple_match(self) -> None:
        response = FakeResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; Secure; Max-Age=1234")]
        )
        response.assert_set_cookie("Foo", "Bar")

    def test_assert_set_cookie__no_cookie_header(self) -> None:
        response = FakeResponse("200 OK", [])
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    def test_assert_set_cookie__no_cookie_value(self) -> None:
        response = FakeResponse("200 OK", [("Set-Cookie", "Foo")])
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    def test_assert_set_cookie__wrong_name(self) -> None:
        response = FakeResponse("200 OK", [("Set-Cookie", "Wrong=Bar")])
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    def test_assert_set_cookie__wrong_value(self) -> None:
        response = FakeResponse("200 OK", [("Set-Cookie", "Foo=Wrong")])
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    def test_assert_set_cookie__has_secure(self) -> None:
        response = FakeResponse("200 OK", [("Set-Cookie", "Foo=Bar; Secure")])
        response.assert_set_cookie("Foo", "Bar")
        response.assert_set_cookie("Foo", "Bar", secure=True)
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", secure=False)

    def test_assert_set_cookie__no_secure(self) -> None:
        response = FakeResponse("200 OK", [("Set-Cookie", "Foo=Bar")])
        response.assert_set_cookie("Foo", "Bar")
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", secure=True)
        response.assert_set_cookie("Foo", "Bar", secure=False)

    def test_assert_set_cookie__has_http_only(self) -> None:
        response = FakeResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; HttpOnly")]
        )
        response.assert_set_cookie("Foo", "Bar")
        response.assert_set_cookie("Foo", "Bar", http_only=True)
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", http_only=False)

    def test_assert_set_cookie__no_http_only(self) -> None:
        response = FakeResponse("200 OK", [("Set-Cookie", "Foo=Bar")])
        response.assert_set_cookie("Foo", "Bar")
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", http_only=True)
        response.assert_set_cookie("Foo", "Bar", http_only=False)

    def test_assert_set_cookie__has_max_age(self) -> None:
        response = FakeResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; Max-Age=1234")]
        )
        response.assert_set_cookie("Foo", "Bar")
        response.assert_set_cookie("Foo", "Bar", max_age=1234)
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", max_age=9999)

    def test_assert_set_cookie__invalid_max_age(self) -> None:
        response = FakeResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; Max-Age=INVALID")]
        )
        response.assert_set_cookie("Foo", "Bar")
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", max_age=1234)

    def test_assert_set_cookie__no_max_age(self) -> None:
        response = FakeResponse("200 OK", [("Set-Cookie", "Foo=Bar")])
        response.assert_set_cookie("Foo", "Bar")
        with pytest.raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", max_age=1234)


class TestWSGIAppTest:
    def test_run_app(self) -> None:
        app_run = False
        env: WSGIEnvironment | None = None

        def app(
            environ: WSGIEnvironment, sr: StartResponse
        ) -> Iterable[bytes]:
            nonlocal app_run, env
            app_run = True
            env = environ
            sr("200 OK", [])
            return []

        request = create_request("GET", "/foo/bar")
        request.add_argument("foo", "bar")
        run_wsgi_test(app, request)
        assert app_run, "app not run"
        assert env is not None
        assert env.get("QUERY_STRING") == "foo=bar"

    def test_response(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            sr("404 Not Found", [("X-Foo", "Bar")])
            return []

        request = create_request("GET", "/foo/bar")
        response = run_wsgi_test(app, request)
        response.assert_status(HTTPStatus.NOT_FOUND)
        response.assert_header_equal("X-Foo", "Bar")

    def test_response_body_without_close(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"Abc")
            writer(b"def")
            return [b"Foo", b"bar"]

        request = create_request("GET", "/foo/bar")
        response = run_wsgi_test(app, request)
        assert response.body == b"AbcdefFoobar"

    def test_response_body_with_close(self) -> None:
        file = BytesIO(b"Foo")

        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"Abc")
            writer(b"def")
            return file

        request = create_request("GET", "/foo/bar")
        response = run_wsgi_test(app, request)
        assert response.body == b"AbcdefFoo"
        assert file.closed

    def test_start_response_not_called(self) -> None:
        def app(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            return []

        request = create_request("GET", "/foo/bar")
        with pytest.raises(AssertionError):
            run_wsgi_test(app, request)

    def test_start_response_called_multiple_times(self) -> None:
        assert_raised = False

        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            nonlocal assert_raised
            sr("200 OK", [])
            try:
                sr("404 Not Found", [])
            except AssertionError:
                assert_raised = True
            return []

        request = create_request("GET", "/foo/bar")
        run_wsgi_test(app, request)
        assert assert_raised

    def test_start_response_called_multiple_times_with_exc_info(self) -> None:
        assert_raised = False

        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            nonlocal assert_raised
            sr("200 OK", [])
            try:
                sr("404 Not Found", [], _get_exc_info())
            except AssertionError:
                assert_raised = True
            return []

        request = create_request("GET", "/foo/bar")
        run_wsgi_test(app, request)
        assert not assert_raised

    def test_start_response_called_after_output_written(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"abc")
            sr("404 OK", [], _get_exc_info())
            return []

        request = create_request("GET", "/foo/bar")
        with pytest.raises(ValueError):
            run_wsgi_test(app, request)

    def test_start_response_called_no_output_written(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"")
            sr("404 OK", [], _get_exc_info())
            return []

        request = create_request("GET", "/foo/bar")
        response = run_wsgi_test(app, request)
        response.assert_status(HTTPStatus.NOT_FOUND)


def _get_exc_info() -> tuple[Any, Any, Any]:
    try:
        raise ValueError()
    except:  # noqa
        return sys.exc_info()


class TestWSGIArgumentsTest:
    def _create_app(
        self, argument_template: Sequence[ArgumentTemplate]
    ) -> WSGIApplication:
        def app(env: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            try:
                parse_args(env, argument_template)
            except ArgumentsError:
                sr("400 Bad Request", [])
            else:
                sr("200 OK", [])
            return []

        return app

    def _successful_arg_test(
        self,
        app_args: Sequence[ArgumentTemplate],
        expected_args: Iterable[ArgumentToTest],
    ) -> None:
        app = self._create_app(app_args)
        request = create_request("GET", "/")
        run_wsgi_arguments_test(app, request, expected_args)

    def _failing_arg_test(
        self,
        app_args: Sequence[ArgumentTemplate],
        expected_args: Iterable[ArgumentToTest],
    ) -> None:
        app = self._create_app(app_args)
        request = create_request("GET", "/")
        with pytest.raises(AssertionError):
            run_wsgi_arguments_test(app, request, expected_args)

    def test_no_expected_args(self) -> None:
        self._successful_arg_test([], [])

    def test_required_argument_present(self) -> None:
        self._successful_arg_test(
            [("arg", int, Multiplicity.REQUIRED)],
            [("arg", Multiplicity.REQUIRED, "42")],
        )

    def test_required_argument_not_in_app(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.REQUIRED, "42")],
        )

    def test_required_argument_not_in_test(self) -> None:
        self._failing_arg_test([("arg", int, Multiplicity.REQUIRED)], [])

    def test_required_argument_optional_in_test(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.REQUIRED)],
            [("arg", Multiplicity.OPTIONAL, "42")],
        )

    def test_required_any_argument_present(self) -> None:
        self._successful_arg_test(
            [("arg", int, Multiplicity.REQUIRED_ANY)],
            [("arg", Multiplicity.REQUIRED_ANY, "42")],
        )

    def test_required_any_argument_not_in_app(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.REQUIRED_ANY, "42")],
        )

    def test_required_any_argument_not_in_test(self) -> None:
        self._failing_arg_test([("arg", int, Multiplicity.REQUIRED_ANY)], [])

    def test_required_any_argument_optional_in_test(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.REQUIRED_ANY)],
            [("arg", Multiplicity.OPTIONAL, "42")],
        )

    def test_optional_argument_not_in_app(self) -> None:
        self._successful_arg_test([], [("arg", Multiplicity.OPTIONAL, "foo")])

    def test_optional_argument_not_in_test(self) -> None:
        self._successful_arg_test([("arg", int, Multiplicity.OPTIONAL)], [])

    def test_any_argument_not_in_app(self) -> None:
        self._successful_arg_test([], [("arg", Multiplicity.ANY, "foo")])

    def test_any_argument_not_in_test(self) -> None:
        self._successful_arg_test([("arg", int, Multiplicity.ANY)], [])

    def test_correct_value_not_accepted(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.OPTIONAL, "not-a-number")],
        )

    def test_invalid_value_accepted(self) -> None:
        self._failing_arg_test(
            [("arg", str, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.OPTIONAL, "42", "not-a-number")],
        )

    def test_handle_other_errors(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            sr("500 Internal Server Error", [])
            return []

        request = create_request("POST", "/")
        with pytest.raises(AssertionError):
            run_wsgi_arguments_test(app, request, [])

    def test_post_request__no_args(self) -> None:
        app = self._create_app([("arg", int, Multiplicity.OPTIONAL)])
        request = create_request("POST", "/")
        run_wsgi_arguments_test(app, request, [])
