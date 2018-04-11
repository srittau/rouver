from http import HTTPStatus
from json import loads as json_decode
from unittest import TestCase

from asserts import assert_equal, assert_in, assert_raises

from werkzeug.wrappers import Request

from rouver.response import \
    respond, respond_with_json, respond_with_html, created_at, see_other, \
    created_as_json, temporary_redirect, respond_with_content

from rouver_test.util import TestingStartResponse, default_environment


class RespondTest(TestCase):
    def test_default_status(self) -> None:
        sr = TestingStartResponse()
        respond(sr)
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = TestingStartResponse()
        respond(sr, status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond(
            sr, extra_headers=[
                ("X-Custom-Header", "Foobar"),
            ])
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_no_content_type(self) -> None:
        sr = TestingStartResponse()
        respond(sr)
        sr.assert_header_missing("Content-Type")

    def test_content_type(self) -> None:
        sr = TestingStartResponse()
        respond(sr, content_type="image/png")
        sr.assert_header_equals("Content-Type", "image/png")

    def test_content_type_in_extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond(sr, extra_headers=[("Content-Type", "image/png")])
        sr.assert_header_equals("Content-Type", "image/png")

    def test_error_if_content_type_also_in_extra_headers(self) -> None:
        sr = TestingStartResponse()
        with assert_raises(ValueError):
            respond(
                sr,
                content_type="image/png",
                extra_headers=[
                    ("Content-Type", "image/jpeg"),
                ])

    def test_response(self) -> None:
        sr = TestingStartResponse()
        response = respond(sr)
        assert_equal(b'', b"".join(response))


class RespondWithContentTest(TestCase):
    def test_default_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"")
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"", status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_default_content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"")
        sr.assert_header_equals("Content-Type", "application/octet-stream")

    def test_custom_content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"", content_type="text/plain")
        sr.assert_header_equals("Content-Type", "text/plain")

    def test_content_length(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(sr, b"foobar")
        sr.assert_header_equals("Content-Length", "6")

    def test_extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond_with_content(
            sr, b"", extra_headers=[
                ("X-Custom-Header", "Foobar"),
            ])
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_return_value(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_content(sr, b"foobar")
        assert_equal(b"foobar", b"".join(response))


class RespondWithJSONTest(TestCase):
    def test_default_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {})
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {}, status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {})
        sr.assert_header_equals("Content-Type",
                                "application/json; charset=utf-8")

    def test_content_length(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(sr, {"foo": 33})
        sr.assert_header_equals("Content-Length", "11")

    def test_extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond_with_json(
            sr, {}, extra_headers=[
                ("X-Custom-Header", "Foobar"),
            ])
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_json_as_bytes(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_json(sr, b'{"foo": 3}')
        assert_equal(b'{"foo": 3}', b"".join(response))

    def test_json_as_str(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_json(sr, '{"föo": 3}')
        assert_equal('{"föo": 3}'.encode("utf-8"), b"".join(response))

    def test_json_as_object(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_json(sr, {"föo": 3})
        assert_equal(b'{"f\\u00f6o": 3}', b"".join(response))


class RespondWithHTMLTest(TestCase):
    def test_default_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(
            sr, "<div>Test</div>", status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_content_type(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")

    def test_content_length(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_header_equals("Content-Length", "15")

    def test_extra_headers(self) -> None:
        sr = TestingStartResponse()
        respond_with_html(
            sr,
            "<div>Täst</div>",
            extra_headers=[
                ("X-Custom-Header", "Foobar"),
            ])
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_return_value(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_html(sr, "<div>Test</div>")
        assert_equal(b"<div>Test</div>", b"".join(response))

    def test_return_value_encoding(self) -> None:
        sr = TestingStartResponse()
        response = respond_with_html(sr, "<div>Täst</div>")
        assert_equal("<div>Täst</div>".encode("utf-8"), b"".join(response))


class CreatedAtTest(TestCase):
    def setUp(self) -> None:
        self.environment = default_environment()
        self.start_request = TestingStartResponse()

    def test_headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_at(request, self.start_request, "/foo/bar")
        self.start_request.assert_status(HTTPStatus.CREATED)
        self.start_request.assert_header_equals("Content-Type",
                                                "text/html; charset=utf-8")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_at(request, self.start_request, "foo/bar")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_non_utf8_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        with assert_raises(ValueError):
            created_at(request, self.start_request, "foo/bär")

    def test_html(self) -> None:
        request = Request(self.environment)
        response = created_at(request, self.start_request, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")


class CreatedAsJSONTest(TestCase):
    def setUp(self) -> None:
        self.environment = default_environment()
        self.start_request = TestingStartResponse()

    def test_headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_as_json(request, self.start_request, "/foo/bar", {})
        self.start_request.assert_status(HTTPStatus.CREATED)
        self.start_request.assert_header_equals(
            "Content-Type", "application/json; charset=utf-8")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        created_as_json(request, self.start_request, "foo/bar", {})
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_non_utf8_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        with assert_raises(ValueError):
            created_as_json(request, self.start_request, "foo/bär", {})

    def test_json(self) -> None:
        request = Request(self.environment)
        response = created_as_json(request, self.start_request, "foo/bar", {
            "foo": 3,
        })
        json = json_decode(b"".join(response).decode("utf-8"))
        assert_equal({"foo": 3}, json)


class TemporaryRedirectTest(TestCase):
    def setUp(self) -> None:
        self.environment = default_environment()
        self.start_request = TestingStartResponse()

    def test_headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        temporary_redirect(request, self.start_request, "/foo/bar")
        self.start_request.assert_status(HTTPStatus.TEMPORARY_REDIRECT)
        self.start_request.assert_header_equals("Content-Type",
                                                "text/html; charset=utf-8")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        temporary_redirect(request, self.start_request, "foo/bar")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_non_utf8_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        with assert_raises(ValueError):
            temporary_redirect(request, self.start_request, "foo/bär")

    def test_do_not_encode_cgi_arguments(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        temporary_redirect(request, self.start_request,
                           "foo?bar=baz&abc=%6A;+,@:$")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo?bar=baz&abc=%6A;+,@:$")

    def test_html(self) -> None:
        request = Request(self.environment)
        response = temporary_redirect(request, self.start_request, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert_in("http://www.example.com/foo/bar", html)


class SeeOtherTest(TestCase):
    def setUp(self) -> None:
        self.environment = default_environment()
        self.start_request = TestingStartResponse()

    def test_headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        see_other(request, self.start_request, "/foo/bar")
        self.start_request.assert_status(HTTPStatus.SEE_OTHER)
        self.start_request.assert_header_equals("Content-Type",
                                                "text/html; charset=utf-8")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        see_other(request, self.start_request, "foo/bar")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_non_utf8_url(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        with assert_raises(ValueError):
            see_other(request, self.start_request, "foo/bär")

    def test_html(self) -> None:
        request = Request(self.environment)
        response = see_other(request, self.start_request, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert_in("http://www.example.com/foo/bar", html)
