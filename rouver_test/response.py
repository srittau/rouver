from http import HTTPStatus
from json import loads as json_decode

from asserts import assert_equal, assert_in, assert_raises
from dectest import TestCase, before, test
from werkzeug.wrappers import Request

from rouver.response import (
    created_as_json,
    created_at,
    respond,
    respond_with_content,
    respond_with_html,
    respond_with_json,
    see_other,
    temporary_redirect,
)
from rouver_test.testutil import TestingStartResponse, default_environment


class RespondTest(TestCase):
    @test
    def default_status(self) -> None:
        sr = TestingStartResponse()
        respond(sr)
        sr.assert_status(HTTPStatus.OK)

    @test
    def custom_status(self) -> None:
        sr = TestingStartResponse()
        respond(sr, status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    @test
    def extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond(sr, extra_headers=[("X-Custom-Header", "Foobar")])
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    @test
    def no_content_type(self) -> None:
        sr = TestingStartResponse()
        respond(sr)
        sr.assert_header_missing("Content-Type")

    @test
    def content_type(self) -> None:
        sr = TestingStartResponse()
        respond(sr, content_type="image/png")
        sr.assert_header_equals("Content-Type", "image/png")

    @test
    def content_type_in_extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond(sr, extra_headers=[("Content-Type", "image/png")])
        sr.assert_header_equals("Content-Type", "image/png")

    @test
    def error_if_content_type_also_in_extra_headers(self) -> None:
        sr = TestingStartResponse()
        with assert_raises(ValueError):
            respond(
                sr,
                content_type="image/png",
                extra_headers=[("Content-Type", "image/jpeg")],
            )

    @test
    def response(self) -> None:
        sr = TestingStartResponse()
        response = respond(sr)
        assert_equal(b"", b"".join(response))


class RespondWithContentTest(TestCase):
    @test
    def default_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"")
        sr.assert_status(HTTPStatus.OK)

    @test
    def custom_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"", status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    @test
    def default_content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"")
        sr.assert_header_equals("Content-Type", "application/octet-stream")

    @test
    def custom_content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"", content_type="text/plain")
        sr.assert_header_equals("Content-Type", "text/plain")

    @test
    def content_length(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"foobar")
        sr.assert_header_equals("Content-Length", "6")

    @test
    def extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(
            sr, b"", extra_headers=[("X-Custom-Header", "Foobar")]
        )
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    @test
    def return_value(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_content(sr, b"foobar")
        assert_equal(b"foobar", b"".join(response))


class RespondWithJSONTest(TestCase):
    @test
    def default_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {})
        sr.assert_status(HTTPStatus.OK)

    @test
    def custom_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {}, status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    @test
    def content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {})
        sr.assert_header_equals(
            "Content-Type", "application/json; charset=utf-8"
        )

    @test
    def content_length(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {"foo": 33})
        sr.assert_header_equals("Content-Length", "11")

    @test
    def extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(
            sr, {}, extra_headers=[("X-Custom-Header", "Foobar")]
        )
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    @test
    def json_as_bytes(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_json(sr, b'{"foo": 3}')
        assert_equal(b'{"foo": 3}', b"".join(response))

    @test
    def json_as_str(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_json(sr, '{"föo": 3}')
        assert_equal('{"föo": 3}'.encode("utf-8"), b"".join(response))

    @test
    def json_as_object(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_json(sr, {"föo": 3})
        assert_equal(b'{"f\\u00f6o": 3}', b"".join(response))


class RespondWithHTMLTest(TestCase):
    @test
    def default_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_status(HTTPStatus.OK)

    @test
    def custom_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(
            sr, "<div>Test</div>", status=HTTPStatus.NOT_ACCEPTABLE
        )
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    @test
    def content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")

    @test
    def content_length(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_header_equals("Content-Length", "15")

    @test
    def extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(
            sr,
            "<div>Täst</div>",
            extra_headers=[("X-Custom-Header", "Foobar")],
        )
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    @test
    def return_value(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_html(sr, "<div>Test</div>")
        assert_equal(b"<div>Test</div>", b"".join(response))

    @test
    def return_value_encoding(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_html(sr, "<div>Täst</div>")
        assert_equal("<div>Täst</div>".encode("utf-8"), b"".join(response))


class CreatedAtTest(TestCase):
    @before
    def setup_environment(self) -> None:
        self.environment = default_environment()
        self.start_response = TestingStartResponse()

    @test
    def headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_at(request, self.start_response, "/foo/bar")
        self.start_response.assert_status(HTTPStatus.CREATED)
        self.start_response.assert_header_equals(
            "Content-Type", "text/html; charset=utf-8"
        )
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/bar"
        )

    @test
    def absolute_url(self) -> None:
        request = Request(self.environment)
        created_at(request, self.start_response, "http://example.com/foo")
        self.start_response.assert_header_equals(
            "Location", "http://example.com/foo"
        )

    @test
    def url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_at(request, self.start_response, "foo/bar")
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/bar"
        )

    @test
    def umlauts_in_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_at(request, self.start_response, "foo/bär")
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    @test
    def extra_headers(self) -> None:
        request = Request(self.environment)
        created_at(
            request,
            self.start_response,
            "foo",
            extra_headers=[("X-Foo", "Bar")],
        )
        self.start_response.assert_header_equals("X-Foo", "Bar")

    @test
    def html(self) -> None:
        request = Request(self.environment)
        response = created_at(request, self.start_response, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")


class CreatedAsJSONTest(TestCase):
    @before
    def setup_environment(self) -> None:
        self.environment = default_environment()
        self.start_response = TestingStartResponse()

    @test
    def headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_as_json(request, self.start_response, "/foo/bar", {})
        self.start_response.assert_status(HTTPStatus.CREATED)
        self.start_response.assert_header_equals(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/bar"
        )

    @test
    def absolute_url(self) -> None:
        request = Request(self.environment)
        created_as_json(
            request, self.start_response, "http://example.com/foo", {}
        )
        self.start_response.assert_header_equals(
            "Location", "http://example.com/foo"
        )

    @test
    def url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_as_json(request, self.start_response, "foo/bar", {})
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/bar"
        )

    @test
    def umlauts_in_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_as_json(request, self.start_response, "foo/bär", {})
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    @test
    def extra_headers(self) -> None:
        request = Request(self.environment)
        created_as_json(
            request,
            self.start_response,
            "foo",
            {},
            extra_headers=[("X-Foo", "Bar")],
        )
        self.start_response.assert_header_equals("X-Foo", "Bar")

    @test
    def json(self) -> None:
        request = Request(self.environment)
        response = created_as_json(
            request, self.start_response, "foo/bar", {"foo": 3}
        )
        json = json_decode(b"".join(response).decode("utf-8"))
        assert_equal({"foo": 3}, json)


class TemporaryRedirectTest(TestCase):
    @before
    def setup_environment(self) -> None:
        self.environment = default_environment()
        self.start_response = TestingStartResponse()

    @test
    def headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        temporary_redirect(request, self.start_response, "/foo/bar")
        self.start_response.assert_status(HTTPStatus.TEMPORARY_REDIRECT)
        self.start_response.assert_header_equals(
            "Content-Type", "text/html; charset=utf-8"
        )
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/bar"
        )

    @test
    def absolute_url(self) -> None:
        request = Request(self.environment)
        temporary_redirect(
            request, self.start_response, "http://example.com/foo"
        )
        self.start_response.assert_header_equals(
            "Location", "http://example.com/foo"
        )

    @test
    def url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        temporary_redirect(request, self.start_response, "foo/bar")
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/bar"
        )

    @test
    def umlauts_in_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        temporary_redirect(request, self.start_response, "foo/bär")
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    @test
    def do_not_encode_cgi_arguments(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        temporary_redirect(
            request, self.start_response, "foo?bar=baz&abc=%6A;+,@:$"
        )
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo?bar=baz&abc=%6A;+,@:$"
        )

    @test
    def extra_headers(self) -> None:
        request = Request(self.environment)
        temporary_redirect(
            request,
            self.start_response,
            "foo",
            extra_headers=[("X-Foo", "Bar")],
        )
        self.start_response.assert_header_equals("X-Foo", "Bar")

    @test
    def html(self) -> None:
        request = Request(self.environment)
        response = temporary_redirect(request, self.start_response, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert_in("http://www.example.com/foo/bar", html)


class SeeOtherTest(TestCase):
    @before
    def setup_environment(self) -> None:
        self.environment = default_environment()
        self.start_response = TestingStartResponse()

    @test
    def headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        see_other(request, self.start_response, "/foo/bar")
        self.start_response.assert_status(HTTPStatus.SEE_OTHER)
        self.start_response.assert_header_equals(
            "Content-Type", "text/html; charset=utf-8"
        )
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/bar"
        )

    @test
    def absolute_url(self) -> None:
        request = Request(self.environment)
        see_other(request, self.start_response, "http://example.com/foo")
        self.start_response.assert_header_equals(
            "Location", "http://example.com/foo"
        )

    @test
    def url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        self.environment["PATH_INFO"] = "/abc/def/"
        request = Request(self.environment)
        see_other(request, self.start_response, "foo/bar")
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/abc/def/foo/bar"
        )

    @test
    def url_path_without_trailing_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        self.environment["PATH_INFO"] = "/abc/def"
        request = Request(self.environment)
        see_other(request, self.start_response, "foo/bar")
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/abc/foo/bar"
        )

    @test
    def umlauts_in_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        see_other(request, self.start_response, "foo/bär")
        self.start_response.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    @test
    def extra_headers(self) -> None:
        request = Request(self.environment)
        see_other(
            request,
            self.start_response,
            "foo",
            extra_headers=[("X-Foo", "Bar")],
        )
        self.start_response.assert_header_equals("X-Foo", "Bar")

    @test
    def html(self) -> None:
        request = Request(self.environment)
        response = see_other(request, self.start_response, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert_in("http://www.example.com/foo/bar", html)
