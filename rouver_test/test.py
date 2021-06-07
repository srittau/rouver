from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from http import HTTPStatus
from io import BytesIO
from typing import Any

from asserts import (
    assert_dict_superset,
    assert_equal,
    assert_false,
    assert_has_attr,
    assert_is_instance,
    assert_is_none,
    assert_not_in,
    assert_raises,
    assert_succeeds,
    assert_true,
)
from dectest import TestCase, test
from werkzeug.formparser import parse_form_data

from rouver.args import ArgumentTemplate, Multiplicity, parse_args
from rouver.exceptions import ArgumentsError
from rouver.test import (
    ArgumentToTest,
    TestRequest,
    TestResponse,
    create_request,
    test_wsgi_app,
    test_wsgi_arguments,
)
from rouver.types import StartResponse, WSGIApplication, WSGIEnvironment


def assert_wsgi_input_stream(stream: object) -> None:
    assert_has_attr(stream, "read")
    assert_has_attr(stream, "readline")
    assert_has_attr(stream, "readlines")
    assert_has_attr(stream, "__iter__")


class TestRequestTest(TestCase):
    @test
    def attributes(self) -> None:
        request = create_request("GET", "/foo/bar")
        assert_equal("GET", request.method)
        assert_equal("/foo/bar", request.path)
        assert_is_none(request.content_type)
        assert_is_instance(request.error_stream, BytesIO)

    @test
    def capitalize_method(self) -> None:
        request = create_request("pOst", "/foo/bar")
        assert_equal("POST", request.method)

    @test
    def to_environment__minimal(self) -> None:
        request = create_request("GET", "/foo/bar")
        environ = request.to_environment()
        assert_dict_superset(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/foo/bar",
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
            },
            environ,
        )
        assert_wsgi_input_stream(environ["wsgi.input"])
        assert_equal(b"", environ["wsgi.input"].read())
        assert_not_in("CONTENT_TYPE", environ)
        assert_not_in("CONTENT_LENGTH", environ)
        assert_not_in("QUERY_STRING", environ)

    @test
    def to_environment__post(self) -> None:
        request = create_request("POST", "/foo/bar")
        environ = request.to_environment()
        assert_dict_superset(
            {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/foo/bar",
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
            },
            environ,
        )
        assert_wsgi_input_stream(environ["wsgi.input"])
        assert_equal(b"", environ["wsgi.input"].read())
        assert_not_in("CONTENT_TYPE", environ)
        assert_not_in("CONTENT_LENGTH", environ)
        assert_not_in("QUERY_STRING", environ)

    @test
    def to_environment__post_urlencoded(self) -> None:
        request = create_request("POST", "/foo/bar")
        request.add_argument("arg", "value")
        environ = request.to_environment()
        assert_dict_superset(
            {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": "application/x-www-form-urlencoded",
                "CONTENT_LENGTH": "9",
            },
            environ,
        )
        assert_wsgi_input_stream(environ["wsgi.input"])
        assert_equal(b"arg=value", environ["wsgi.input"].read())
        assert_not_in("QUERY_STRING", environ)

    @test
    def set_env_var(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_env_var("foo.bar", "baz")
        environ = request.to_environment()
        assert_dict_superset({"foo.bar": "baz"}, environ)

    @test
    def set_env_var__priority(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_env_var("SERVER_PORT", "8888")
        request.set_env_var("HTTP_X_FOO", "Set by env var")
        request.set_header("X-Foo", "Set by header")
        environ = request.to_environment()
        assert_dict_superset(
            {"SERVER_PORT": "8888", "HTTP_X_FOO": "Set by env var"}, environ
        )

    @test
    def set_header(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_header("X-Foobar", "Baz")
        environ = request.to_environment()
        assert_dict_superset({"HTTP_X_FOOBAR": "Baz"}, environ)

    @test
    def set_header__content_type(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.set_header("Content-Type", "text/html")
        assert_equal("text/html", request.content_type)
        environ = request.to_environment()
        assert_dict_superset({"CONTENT_TYPE": "text/html"}, environ)
        assert_not_in("HTTP_CONTENT_TYPE", environ)

    @test
    def add_argument__content_type(self) -> None:
        request = create_request("POST", "/foo/bar")
        assert_is_none(request.content_type)
        request.add_argument("foo", "bar")
        assert_is_none(request.content_type)
        environ = request.to_environment()
        assert_dict_superset(
            {"CONTENT_TYPE": "application/x-www-form-urlencoded"}, environ
        )

        request = create_request("POST", "/foo/bar")
        request.content_type = "image/png"
        request.add_argument("abc", "def")
        assert_equal("image/png", request.content_type)
        environ = request.to_environment()
        assert_dict_superset({"CONTENT_TYPE": "image/png"}, environ)

        request = create_request("GET", "/foo/bar")
        assert_is_none(request.content_type)
        request.add_argument("foo", "bar")
        assert_is_none(request.content_type)
        environ = request.to_environment()
        assert_not_in("CONTENT_TYPE", environ)

    @test
    def add_file_argument__content_type(self) -> None:
        request = create_request("POST", "/foo/bar")
        assert_is_none(request.content_type)
        request.add_file_argument("foo", b"", "text/plain")
        assert_is_none(request.content_type)
        environ = request.to_environment()
        content_type, boundary = environ["CONTENT_TYPE"].split(";")
        assert_equal("multipart/form-data", content_type)

        request = create_request("POST", "/foo/bar")
        request.content_type = "image/png"
        request.add_file_argument("abc", b"", "text/plain")
        assert_equal("image/png", request.content_type)
        environ = request.to_environment()
        assert_dict_superset({"CONTENT_TYPE": "image/png"}, environ)

    @test
    def add_argument__body_set(self) -> None:
        put_request = create_request("PUT", "/foo")
        put_request.body = b"Body"
        with assert_raises(ValueError):
            put_request.add_argument("foo", "bar")

    @test
    def add_file_argument__body_set(self) -> None:
        put_request = create_request("PUT", "/foo")
        put_request.body = b"Body"
        with assert_raises(ValueError):
            put_request.add_file_argument("foo", b"", "text/plain")

    @test
    def add_file_argument__unsupported_method(self) -> None:
        get_request = create_request("GET", "/foo")
        with assert_raises(ValueError):
            get_request.add_file_argument("foo", b"", "text/plain")

    @test
    def to_environment__content_type(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.content_type = "image/png"
        environ = request.to_environment()
        assert_dict_superset({"CONTENT_TYPE": "image/png"}, environ)

    @test
    def arguments__get_request(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("foo", "bar")
        request.add_argument("abc", ["def", "ghi"])
        environ = request.to_environment()
        assert_dict_superset(
            {"QUERY_STRING": "foo=bar&abc=def&abc=ghi"}, environ
        )

    @test
    def arguments__put_request(self) -> None:
        request = create_request("PUT", "/foo")
        request.add_argument("foo", "bar")
        request.add_argument("abc", ["def", "ghi"])
        environ = request.to_environment()
        assert_not_in("QUERY_STRING", environ)
        assert_equal(
            "application/x-www-form-urlencoded", environ["CONTENT_TYPE"]
        )
        content = environ["wsgi.input"].read()
        assert_equal(b"foo=bar&abc=def&abc=ghi", content)

    @test
    def arguments__quote(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("föo", "bär")
        environ = request.to_environment()
        assert_dict_superset({"QUERY_STRING": "f%C3%B6o=b%C3%A4r"}, environ)

    @test
    def file_arguments(self) -> None:
        request = create_request("PUT", "/foo")
        request.add_argument("foo", "bar")
        request.add_file_argument("file1", b"content1", "text/plain")
        request.add_file_argument(
            "file2", b"content2", "image/png", filename="foobar"
        )
        environ = request.to_environment()
        assert_not_in("QUERY_STRING", environ)
        content_type, boundary = environ["CONTENT_TYPE"].split(";")
        assert_equal("multipart/form-data", content_type)
        _, args, files = parse_form_data(environ)
        assert_equal(1, len(args))
        assert_equal(args["foo"], "bar")
        assert_equal(2, len(files))
        file1 = files["file1"]
        assert_equal("text/plain", file1.mimetype)
        assert_equal("", file1.filename)
        assert_equal(b"content1", file1.stream.read())
        file2 = files["file2"]
        assert_equal("image/png", file2.mimetype)
        assert_equal("foobar", file2.filename)
        assert_equal(b"content2", file2.stream.read())

    @test
    def file_arguments__umlauts(self) -> None:
        request = create_request("PUT", "/foo")
        request.add_argument('f"öo', "bär")
        request.add_file_argument(
            'f"öle', b"", "text/plain", filename="ä\"'bc"
        )
        environ = request.to_environment()
        assert_not_in("QUERY_STRING", environ)
        content_type, boundary = environ["CONTENT_TYPE"].split(";")
        assert_equal("multipart/form-data", content_type)
        _, args, files = parse_form_data(environ)
        assert_equal(1, len(args))
        assert_equal(args["f%22%C3%B6o"], "bär")
        assert_equal(1, len(files))
        file = files["f%22%C3%B6le"]
        assert_equal("text/plain", file.mimetype)
        assert_equal("ä\"'bc", file.filename)
        assert_equal(b"", file.stream.read())

    @test
    def clear_arguments(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("foo", "bar")
        request.clear_arguments()
        environ = request.to_environment()
        assert_not_in("QUERY_STRING", environ)

        request = create_request("POST", "/foo")
        request.add_argument("foo", "bar")
        request.clear_arguments()
        environ = request.to_environment()
        content = environ["wsgi.input"].read()
        assert_equal(b"", content)

    @test
    def body(self) -> None:
        request = create_request("POST", "/")
        assert_equal(b"", request.body)
        request.body = b"Test Body"
        assert_equal(b"Test Body", request.body)
        environ = request.to_environment()
        assert_equal("9", environ.get("CONTENT_LENGTH"))
        assert_equal(b"Test Body", environ["wsgi.input"].read())

    @test
    def set_body_in_get_request(self) -> None:
        request = create_request("GET", "/")
        with assert_succeeds(ValueError):
            request.body = b""
        with assert_raises(ValueError):
            request.body = b"Test Body"

    @test
    def set_body_when_argument_is_set(self) -> None:
        request = create_request("POST", "/")
        request.add_argument("foo", "bar")
        with assert_raises(ValueError):
            request.body = b""
        with assert_raises(ValueError):
            request.body = b"Body"

    def _assert_json_request(
        self, request: TestRequest, expected_body: bytes
    ) -> None:
        assert_equal(expected_body, request.body)
        env = request.to_environment()
        assert_equal(str(len(expected_body)), env["CONTENT_LENGTH"])
        assert_equal("application/json; charset=utf-8", env["CONTENT_TYPE"])
        assert_equal(expected_body, env["wsgi.input"].read())

    @test
    def set_json_request__get_request(self) -> None:
        request = create_request("GET", "/")
        with assert_raises(ValueError):
            request.set_json_request(b"{}")

    @test
    def set_json_request__bytes(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request(b"{}")
        self._assert_json_request(request, b"{}")

    @test
    def set_json_request__str(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request('{"foo": "bär"}')
        self._assert_json_request(request, '{"foo": "bär"}'.encode("utf-8"))

    @test
    def set_json_request__dict(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request({"foo": "bär"})
        self._assert_json_request(request, b'{"foo": "b\\u00e4r"}')

    @test
    def set_json_request__list(self) -> None:
        request = create_request("POST", "/")
        request.set_json_request(["foo", "bär"])
        self._assert_json_request(request, b'["foo", "b\\u00e4r"]')


class TestResponseTest(TestCase):
    @test
    def attributes(self) -> None:
        response = TestResponse("200 OK", [])
        assert_equal("200 OK", response.status_line)
        assert_equal(HTTPStatus.OK, response.status)
        assert_equal(b"", response.body)

    @test
    def unknown_status(self) -> None:
        with assert_raises(ValueError):
            TestResponse("999 Unknown", [])

    @test
    def invalid_status_line(self) -> None:
        with assert_raises(ValueError):
            TestResponse("INVALID", [])

    @test
    def get_header_value(self) -> None:
        response = TestResponse(
            "200 OK",
            [
                ("X-Header", "Foobar"),
                ("Content-Type", "image/png"),
                ("Allow", "GET"),
            ],
        )
        assert_equal("image/png", response.get_header_value("Content-Type"))
        assert_equal("image/png", response.get_header_value("content-TYPE"))
        with assert_raises(ValueError):
            response.get_header_value("X-Unknown")

    @test
    def parse_json_body(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "application/json")]
        )
        response.body = b'{"foo": 5}'
        json = response.parse_json_body()
        assert_equal({"foo": 5}, json)

    @test
    def parse_json_body__wrong_content_type(self) -> None:
        response = TestResponse("200 OK", [("Content-Type", "text/plain")])
        response.body = b"{}"
        with assert_raises(AssertionError):
            response.parse_json_body()

    @test
    def parse_json_body__wrong_content_encoding(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "application/json; charset=latin1")]
        )
        response.body = b"{}"
        with assert_raises(AssertionError):
            response.parse_json_body()

    @test
    def parse_json_body__invalid_json(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "application/json")]
        )
        response.body = b'{"foo":'
        with assert_raises(AssertionError):
            response.parse_json_body()

    @test
    def parse_json_body__invalid_encoding(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "application/json; charset=utf-8")]
        )
        response.body = '{"föo": 5}'.encode("iso-8859-1")
        with assert_raises(AssertionError):
            response.parse_json_body()

    @test
    def assert_status__ok(self) -> None:
        response = TestResponse("404 Not Found", [])
        with assert_succeeds(AssertionError):
            response.assert_status(HTTPStatus.NOT_FOUND)

    @test
    def assert_status__fail(self) -> None:
        response = TestResponse("404 Not Found", [])
        with assert_raises(AssertionError):
            response.assert_status(HTTPStatus.OK)

    @test
    def assert_header_not_set__is_set(self) -> None:
        response = TestResponse("200 OK", [("X-Foo", "value")])
        with assert_raises(AssertionError):
            response.assert_header_not_set("x-FOO")

    @test
    def assert_header_not_set__not_set(self) -> None:
        response = TestResponse("200 OK", [])
        with assert_succeeds(AssertionError):
            response.assert_header_not_set("X-Foo")

    @test
    def assert_header_equal__no_such_header(self) -> None:
        response = TestResponse("200 OK", [("X-Other", "value")])
        with assert_raises(AssertionError):
            response.assert_header_equal("X-Header", "value")

    @test
    def assert_header_equal__ok(self) -> None:
        response = TestResponse("200 OK", [("X-Header", "value")])
        with assert_succeeds(AssertionError):
            response.assert_header_equal("X-Header", "value")

    @test
    def assert_header_equal__differs(self) -> None:
        response = TestResponse("200 OK", [("X-Header", "other")])
        with assert_raises(AssertionError):
            response.assert_header_equal("X-Header", "value")

    @test
    def assert_created_at__ok(self) -> None:
        response = TestResponse(
            "201 Created", [("Location", "http://example.com/")]
        )
        with assert_succeeds(AssertionError):
            response.assert_created_at("http://example.com/")

    @test
    def assert_created_at__wrong_status(self) -> None:
        response = TestResponse(
            "200 OK", [("Location", "http://example.com/")]
        )
        with assert_raises(AssertionError):
            response.assert_created_at("http://example.com/")

    @test
    def assert_created_at__no_location_header(self) -> None:
        response = TestResponse("201 Created", [])
        with assert_raises(AssertionError):
            response.assert_created_at("http://example.org/")

    @test
    def assert_created_at__wrong_location(self) -> None:
        response = TestResponse(
            "201 Created", [("Location", "http://example.com/")]
        )
        with assert_raises(AssertionError):
            response.assert_created_at("http://example.org/")

    @test
    def assert_created_at__relative_location(self) -> None:
        response = TestResponse(
            "201 Created", [("Location", "http://example.com/foo/bar")]
        )
        with assert_succeeds(AssertionError):
            response.assert_created_at("/foo/bar")

    @test
    def assert_created_at__keep_query_string(self) -> None:
        response = TestResponse(
            "201 Created",
            [("Location", "http://example.com/foo?abc=def#frag")],
        )
        with assert_succeeds(AssertionError):
            response.assert_created_at("/foo?abc=def#frag")

    @test
    def assert_see_other__ok(self) -> None:
        response = TestResponse(
            "303 See Other", [("Location", "http://example.com/")]
        )
        with assert_succeeds(AssertionError):
            response.assert_see_other("http://example.com/")

    @test
    def assert_see_other__wrong_status(self) -> None:
        response = TestResponse(
            "200 OK", [("Location", "http://example.com/")]
        )
        with assert_raises(AssertionError):
            response.assert_see_other("http://example.com/")

    @test
    def assert_see_other__no_location_header(self) -> None:
        response = TestResponse("303 See Other", [])
        with assert_raises(AssertionError):
            response.assert_see_other("http://example.org/")

    @test
    def assert_see_other__wrong_location(self) -> None:
        response = TestResponse(
            "303 See Other", [("Location", "http://example.com/")]
        )
        with assert_raises(AssertionError):
            response.assert_see_other("http://example.org/")

    @test
    def assert_see_other__relative_location(self) -> None:
        response = TestResponse(
            "303 See Other", [("Location", "http://example.com/foo/bar")]
        )
        with assert_succeeds(AssertionError):
            response.assert_see_other("/foo/bar")

    @test
    def assert_see_other__keep_query_string(self) -> None:
        response = TestResponse(
            "303 See Other",
            [("Location", "http://example.com/foo?abc=def#frag")],
        )
        with assert_succeeds(AssertionError):
            response.assert_see_other("/foo?abc=def#frag")

    @test
    def assert_temporary_redirect__ok(self) -> None:
        response = TestResponse(
            "307 Temporary Redirect", [("Location", "http://example.com/")]
        )
        with assert_succeeds(AssertionError):
            response.assert_temporary_redirect("http://example.com/")

    @test
    def assert_temporary_redirect__wrong_status(self) -> None:
        response = TestResponse(
            "200 OK", [("Location", "http://example.com/")]
        )
        with assert_raises(AssertionError):
            response.assert_temporary_redirect("http://example.com/")

    @test
    def assert_temporary_redirect__no_location_header(self) -> None:
        response = TestResponse("307 Temporary Redirect", [])
        with assert_raises(AssertionError):
            response.assert_temporary_redirect("http://example.org/")

    @test
    def assert_temporary_redirect__wrong_location(self) -> None:
        response = TestResponse(
            "307 Temporary Redirect", [("Location", "http://example.com/")]
        )
        with assert_raises(AssertionError):
            response.assert_temporary_redirect("http://example.org/")

    @test
    def assert_temporary_redirect__relative_location(self) -> None:
        response = TestResponse(
            "307 Temporary Redirect",
            [("Location", "http://example.com/foo/bar")],
        )
        with assert_succeeds(AssertionError):
            response.assert_temporary_redirect("/foo/bar")

    @test
    def assert_temporary_redirect__keep_query_string(self) -> None:
        response = TestResponse(
            "307 Temporary Redirect",
            [("Location", "http://example.com/foo?abc=def#frag")],
        )
        with assert_succeeds(AssertionError):
            response.assert_temporary_redirect("/foo?abc=def#frag")

    @test
    def assert_content_type__no_such_header(self) -> None:
        response = TestResponse("200 OK", [])
        with assert_raises(AssertionError):
            response.assert_content_type("image/png")

    @test
    def assert_content_type__equal(self) -> None:
        response = TestResponse("200 OK", [("Content-Type", "image/png")])
        with assert_succeeds(AssertionError):
            response.assert_content_type("image/png")

    @test
    def assert_content_type__different(self) -> None:
        response = TestResponse("200 OK", [("Content-Type", "image/png")])
        with assert_raises(AssertionError):
            response.assert_content_type("image/jpeg")

    @test
    def assert_content_type__charset_matches(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "text/html; charset=us-ascii")]
        )
        with assert_succeeds(AssertionError):
            response.assert_content_type("text/html", charset="us-ascii")

    @test
    def assert_content_type__charset_list_matches(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "text/html; charset=us-ascii")]
        )
        with assert_succeeds(AssertionError):
            response.assert_content_type(
                "text/html", charset=["us-ascii", "utf-8", None]
            )

    @test
    def assert_content_type__charset_list_matches__none(self) -> None:
        response = TestResponse("200 OK", [("Content-Type", "text/html")])
        with assert_succeeds(AssertionError):
            response.assert_content_type(
                "text/html", charset=["us-ascii", "utf-8", None]
            )

    @test
    def assert_content_type__charset_not_checked(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "text/html; charset=utf-8")]
        )
        with assert_succeeds(AssertionError):
            response.assert_content_type("text/html")

    @test
    def assert_content_type__no_charset_in_response(self) -> None:
        response = TestResponse("200 OK", [("Content-Type", "text/html")])
        with assert_raises(AssertionError):
            response.assert_content_type("text/html", charset="us-ascii")

    @test
    def assert_content_type__wrong_charset(self) -> None:
        response = TestResponse(
            "200 OK", [("Content-Type", "text/html; charset=utf-8")]
        )
        with assert_raises(AssertionError):
            response.assert_content_type("text/html", charset="us-ascii")

    @test
    def assert_set_cookie__simple_match(self) -> None:
        response = TestResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; Secure; Max-Age=1234")]
        )
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    @test
    def assert_set_cookie__no_cookie_header(self) -> None:
        response = TestResponse("200 OK", [])
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    @test
    def assert_set_cookie__no_cookie_value(self) -> None:
        response = TestResponse("200 OK", [("Set-Cookie", "Foo")])
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    @test
    def assert_set_cookie__wrong_name(self) -> None:
        response = TestResponse("200 OK", [("Set-Cookie", "Wrong=Bar")])
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    @test
    def assert_set_cookie__wrong_value(self) -> None:
        response = TestResponse("200 OK", [("Set-Cookie", "Foo=Wrong")])
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar")

    @test
    def assert_set_cookie__has_secure(self) -> None:
        response = TestResponse("200 OK", [("Set-Cookie", "Foo=Bar; Secure")])
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar", secure=True)
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", secure=False)

    @test
    def assert_set_cookie__no_secure(self) -> None:
        response = TestResponse("200 OK", [("Set-Cookie", "Foo=Bar")])
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", secure=True)
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar", secure=False)

    @test
    def assert_set_cookie__has_http_only(self) -> None:
        response = TestResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; HttpOnly")]
        )
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar", http_only=True)
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", http_only=False)

    @test
    def assert_set_cookie__no_http_only(self) -> None:
        response = TestResponse("200 OK", [("Set-Cookie", "Foo=Bar")])
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", http_only=True)
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar", http_only=False)

    @test
    def assert_set_cookie__has_max_age(self) -> None:
        response = TestResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; Max-Age=1234")]
        )
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar", max_age=1234)
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", max_age=9999)

    @test
    def assert_set_cookie__invalid_max_age(self) -> None:
        response = TestResponse(
            "200 OK", [("Set-Cookie", "Foo=Bar; Max-Age=INVALID")]
        )
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", max_age=1234)

    @test
    def assert_set_cookie__no_max_age(self) -> None:
        response = TestResponse("200 OK", [("Set-Cookie", "Foo=Bar")])
        with assert_succeeds(AssertionError):
            response.assert_set_cookie("Foo", "Bar")
        with assert_raises(AssertionError):
            response.assert_set_cookie("Foo", "Bar", max_age=1234)


class TestWSGIAppTest(TestCase):
    @test
    def run_app(self) -> None:
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
        test_wsgi_app(app, request)
        assert_true(app_run, "app not run")
        assert env is not None
        assert_equal("foo=bar", env.get("QUERY_STRING"))

    @test
    def response(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            sr("404 Not Found", [("X-Foo", "Bar")])
            return []

        request = create_request("GET", "/foo/bar")
        response = test_wsgi_app(app, request)
        response.assert_status(HTTPStatus.NOT_FOUND)
        response.assert_header_equal("X-Foo", "Bar")

    @test
    def response_body(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"Abc")
            writer(b"def")
            return [b"Foo", b"bar"]

        request = create_request("GET", "/foo/bar")
        response = test_wsgi_app(app, request)
        assert_equal(b"AbcdefFoobar", response.body)

    @test
    def start_response_not_called(self) -> None:
        def app(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            return []

        request = create_request("GET", "/foo/bar")
        with assert_raises(AssertionError):
            test_wsgi_app(app, request)

    @test
    def start_response_called_multiple_times(self) -> None:
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
        test_wsgi_app(app, request)
        assert_true(assert_raised)

    @test
    def start_response_called_multiple_times_with_exc_info(self) -> None:
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
        test_wsgi_app(app, request)
        assert_false(assert_raised)

    @test
    def start_response_called_after_output_written(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"abc")
            sr("404 OK", [], _get_exc_info())
            return []

        request = create_request("GET", "/foo/bar")
        with assert_raises(ValueError):
            test_wsgi_app(app, request)

    @test
    def start_response_called_no_output_written(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"")
            sr("404 OK", [], _get_exc_info())
            return []

        request = create_request("GET", "/foo/bar")
        response = test_wsgi_app(app, request)
        response.assert_status(HTTPStatus.NOT_FOUND)


def _get_exc_info() -> tuple[Any, Any, Any]:
    try:
        raise ValueError()
    except:  # noqa
        return sys.exc_info()


class TestWSGIArgumentsTest(TestCase):
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
        with assert_succeeds(AssertionError):
            test_wsgi_arguments(app, request, expected_args)

    def _failing_arg_test(
        self,
        app_args: Sequence[ArgumentTemplate],
        expected_args: Iterable[ArgumentToTest],
    ) -> None:
        app = self._create_app(app_args)
        request = create_request("GET", "/")
        with assert_raises(AssertionError):
            test_wsgi_arguments(app, request, expected_args)

    @test
    def no_expected_args(self) -> None:
        self._successful_arg_test([], [])

    @test
    def required_argument_present(self) -> None:
        self._successful_arg_test(
            [("arg", int, Multiplicity.REQUIRED)],
            [("arg", Multiplicity.REQUIRED, "42")],
        )

    @test
    def required_argument_not_in_app(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.REQUIRED, "42")],
        )

    @test
    def required_argument_not_in_test(self) -> None:
        self._failing_arg_test([("arg", int, Multiplicity.REQUIRED)], [])

    @test
    def required_argument_optional_in_test(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.REQUIRED)],
            [("arg", Multiplicity.OPTIONAL, "42")],
        )

    @test
    def required_any_argument_present(self) -> None:
        self._successful_arg_test(
            [("arg", int, Multiplicity.REQUIRED_ANY)],
            [("arg", Multiplicity.REQUIRED_ANY, "42")],
        )

    @test
    def required_any_argument_not_in_app(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.REQUIRED_ANY, "42")],
        )

    @test
    def required_any_argument_not_in_test(self) -> None:
        self._failing_arg_test([("arg", int, Multiplicity.REQUIRED_ANY)], [])

    @test
    def required_any_argument_optional_in_test(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.REQUIRED_ANY)],
            [("arg", Multiplicity.OPTIONAL, "42")],
        )

    @test
    def optional_argument_not_in_app(self) -> None:
        self._successful_arg_test([], [("arg", Multiplicity.OPTIONAL, "foo")])

    @test
    def optional_argument_not_in_test(self) -> None:
        self._successful_arg_test([("arg", int, Multiplicity.OPTIONAL)], [])

    @test
    def any_argument_not_in_app(self) -> None:
        self._successful_arg_test([], [("arg", Multiplicity.ANY, "foo")])

    @test
    def any_argument_not_in_test(self) -> None:
        self._successful_arg_test([("arg", int, Multiplicity.ANY)], [])

    @test
    def correct_value_not_accepted(self) -> None:
        self._failing_arg_test(
            [("arg", int, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.OPTIONAL, "not-a-number")],
        )

    @test
    def invalid_value_accepted(self) -> None:
        self._failing_arg_test(
            [("arg", str, Multiplicity.OPTIONAL)],
            [("arg", Multiplicity.OPTIONAL, "42", "not-a-number")],
        )

    @test
    def handle_other_errors(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            sr("500 Internal Server Error", [])
            return []

        request = create_request("POST", "/")
        with assert_raises(AssertionError):
            test_wsgi_arguments(app, request, [])

    @test
    def post_request__no_args(self) -> None:
        app = self._create_app([("arg", int, Multiplicity.OPTIONAL)])
        request = create_request("POST", "/")
        with assert_succeeds(AssertionError):
            test_wsgi_arguments(app, request, [])
