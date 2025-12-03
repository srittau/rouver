from http import HTTPStatus
from json import loads as json_decode

import pytest
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
from rouver_test.testutil import StubStartResponse, default_environment


class TestRespond:
    def test_default_status(self) -> None:
        sr = StubStartResponse()
        respond(sr)
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = StubStartResponse()
        respond(sr, status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_extra_headers(self) -> None:
        sr = StubStartResponse()
        respond(sr, extra_headers=[("X-Custom-Header", "Foobar")])
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_no_content_type(self) -> None:
        sr = StubStartResponse()
        respond(sr)
        sr.assert_header_missing("Content-Type")

    def test_content_type(self) -> None:
        sr = StubStartResponse()
        respond(sr, content_type="image/png")
        sr.assert_header_equals("Content-Type", "image/png")

    def test_content_type_in_extra_headers(self) -> None:
        sr = StubStartResponse()
        respond(sr, extra_headers=[("Content-Type", "image/png")])
        sr.assert_header_equals("Content-Type", "image/png")

    def test_error_if_content_type_also_in_extra_headers(self) -> None:
        sr = StubStartResponse()
        with pytest.raises(ValueError):
            respond(
                sr,
                content_type="image/png",
                extra_headers=[("Content-Type", "image/jpeg")],
            )

    def test_response(self) -> None:
        sr = StubStartResponse()
        response = respond(sr)
        assert b"".join(response) == b""


class TestRespondWithContent:
    def test_default_status(self) -> None:
        sr = StubStartResponse()
        respond_with_content(sr, b"")
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = StubStartResponse()
        respond_with_content(sr, b"", status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_default_content_type(self) -> None:
        sr = StubStartResponse()
        respond_with_content(sr, b"")
        sr.assert_header_equals("Content-Type", "application/octet-stream")

    def test_custom_content_type(self) -> None:
        sr = StubStartResponse()
        respond_with_content(sr, b"", content_type="text/plain")
        sr.assert_header_equals("Content-Type", "text/plain")

    def test_content_length(self) -> None:
        sr = StubStartResponse()
        respond_with_content(sr, b"foobar")
        sr.assert_header_equals("Content-Length", "6")

    def test_extra_headers(self) -> None:
        sr = StubStartResponse()
        respond_with_content(
            sr, b"", extra_headers=[("X-Custom-Header", "Foobar")]
        )
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_return_value(self) -> None:
        sr = StubStartResponse()
        response = respond_with_content(sr, b"foobar")
        assert b"".join(response) == b"foobar"


class TestRespondWithJSON:
    def test_default_status(self) -> None:
        sr = StubStartResponse()
        respond_with_json(sr, {})
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = StubStartResponse()
        respond_with_json(sr, {}, status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_content_type(self) -> None:
        sr = StubStartResponse()
        respond_with_json(sr, {})
        sr.assert_header_equals(
            "Content-Type", "application/json; charset=utf-8"
        )

    def test_content_length(self) -> None:
        sr = StubStartResponse()
        respond_with_json(sr, {"foo": 33})
        sr.assert_header_equals("Content-Length", "11")

    def test_extra_headers(self) -> None:
        sr = StubStartResponse()
        respond_with_json(
            sr, {}, extra_headers=[("X-Custom-Header", "Foobar")]
        )
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_json_as_bytes(self) -> None:
        sr = StubStartResponse()
        response = respond_with_json(sr, b'{"foo": 3}')
        assert b"".join(response) == b'{"foo": 3}'

    def test_json_as_str(self) -> None:
        sr = StubStartResponse()
        response = respond_with_json(sr, '{"föo": 3}')
        assert b"".join(response) == '{"föo": 3}'.encode("utf-8")

    def test_json_as_object(self) -> None:
        sr = StubStartResponse()
        response = respond_with_json(sr, {"föo": 3})
        assert b"".join(response) == b'{"f\\u00f6o": 3}'


class TestRespondWithHTML:
    def test_default_status(self) -> None:
        sr = StubStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = StubStartResponse()
        respond_with_html(
            sr, "<div>Test</div>", status=HTTPStatus.NOT_ACCEPTABLE
        )
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_content_type(self) -> None:
        sr = StubStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")

    def test_content_length(self) -> None:
        sr = StubStartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_header_equals("Content-Length", "15")

    def test_extra_headers(self) -> None:
        sr = StubStartResponse()
        respond_with_html(
            sr,
            "<div>Täst</div>",
            extra_headers=[("X-Custom-Header", "Foobar")],
        )
        sr.assert_header_equals("X-Custom-Header", "Foobar")

    def test_return_value(self) -> None:
        sr = StubStartResponse()
        response = respond_with_html(sr, "<div>Test</div>")
        assert b"".join(response) == b"<div>Test</div>"

    def test_return_value_encoding(self) -> None:
        sr = StubStartResponse()
        response = respond_with_html(sr, "<div>Täst</div>")
        assert b"".join(response) == "<div>Täst</div>".encode("utf-8")


class TestCreatedAt:
    def test_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        created_at(request, sr, "/foo/bar")
        sr.assert_status(HTTPStatus.CREATED)
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")
        sr.assert_header_equals("Location", "http://www.example.com/foo/bar")

    def test_absolute_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        created_at(request, sr, "http://example.com/foo")
        sr.assert_header_equals("Location", "http://example.com/foo")

    def test_url_without_leading_slash(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        created_at(request, sr, "foo/bar")
        sr.assert_header_equals("Location", "http://www.example.com/foo/bar")

    def test_umlauts_in_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        created_at(request, sr, "foo/bär")
        sr.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    def test_extra_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        created_at(
            request,
            sr,
            "foo",
            extra_headers=[("X-Foo", "Bar")],
        )
        sr.assert_header_equals("X-Foo", "Bar")

    def test_html(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        response = created_at(request, sr, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")


class TestCreatedAsJSON:
    def test_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        created_as_json(request, sr, "/foo/bar", {})
        sr.assert_status(HTTPStatus.CREATED)
        sr.assert_header_equals(
            "Content-Type", "application/json; charset=utf-8"
        )
        sr.assert_header_equals("Location", "http://www.example.com/foo/bar")

    def test_absolute_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        created_as_json(request, sr, "http://example.com/foo", {})
        sr.assert_header_equals("Location", "http://example.com/foo")

    def test_url_without_leading_slash(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        created_as_json(request, sr, "foo/bar", {})
        sr.assert_header_equals("Location", "http://www.example.com/foo/bar")

    def test_umlauts_in_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        created_as_json(request, sr, "foo/bär", {})
        sr.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    def test_extra_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        created_as_json(
            request,
            sr,
            "foo",
            {},
            extra_headers=[("X-Foo", "Bar")],
        )
        sr.assert_header_equals("X-Foo", "Bar")

    def test_json(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        response = created_as_json(request, sr, "foo/bar", {"foo": 3})
        json = json_decode(b"".join(response).decode("utf-8"))
        assert json == {"foo": 3}


class TestTemporaryRedirect:
    def test_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        temporary_redirect(request, sr, "/foo/bar")
        sr.assert_status(HTTPStatus.TEMPORARY_REDIRECT)
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")
        sr.assert_header_equals("Location", "http://www.example.com/foo/bar")

    def test_absolute_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        temporary_redirect(request, sr, "http://example.com/foo")
        sr.assert_header_equals("Location", "http://example.com/foo")

    def test_url_without_leading_slash(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        temporary_redirect(request, sr, "foo/bar")
        sr.assert_header_equals("Location", "http://www.example.com/foo/bar")

    def test_umlauts_in_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        temporary_redirect(request, sr, "foo/bär")
        sr.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    def test_do_not_encode_cgi_arguments(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        temporary_redirect(request, sr, "foo?bar=baz&abc=%6A;+,@:$")
        sr.assert_header_equals(
            "Location", "http://www.example.com/foo?bar=baz&abc=%6A;+,@:$"
        )

    def test_extra_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        temporary_redirect(
            request,
            sr,
            "foo",
            extra_headers=[("X-Foo", "Bar")],
        )
        sr.assert_header_equals("X-Foo", "Bar")

    def test_html(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        response = temporary_redirect(request, sr, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert "http://www.example.com/foo/bar" in html


class TestSeeOther:
    def test_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        see_other(request, sr, "/foo/bar")
        sr.assert_status(HTTPStatus.SEE_OTHER)
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")
        sr.assert_header_equals("Location", "http://www.example.com/foo/bar")

    def test_absolute_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        see_other(request, sr, "http://example.com/foo")
        sr.assert_header_equals("Location", "http://example.com/foo")

    def test_url_without_leading_slash(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        env["PATH_INFO"] = "/abc/def/"
        request = Request(env)
        see_other(request, sr, "foo/bar")
        sr.assert_header_equals(
            "Location", "http://www.example.com/abc/def/foo/bar"
        )

    def test_url_path_without_trailing_slash(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        env["PATH_INFO"] = "/abc/def"
        request = Request(env)
        see_other(request, sr, "foo/bar")
        sr.assert_header_equals(
            "Location", "http://www.example.com/abc/foo/bar"
        )

    def test_umlauts_in_url(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        env["SERVER_NAME"] = "www.example.com"
        request = Request(env)
        see_other(request, sr, "foo/bär")
        sr.assert_header_equals(
            "Location", "http://www.example.com/foo/b%C3%A4r"
        )

    def test_extra_headers(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        see_other(
            request,
            sr,
            "foo",
            extra_headers=[("X-Foo", "Bar")],
        )
        sr.assert_header_equals("X-Foo", "Bar")

    def test_html(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        request = Request(env)
        response = see_other(request, sr, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert "http://www.example.com/foo/bar" in html
