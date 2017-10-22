from http import HTTPStatus
from unittest import TestCase

from asserts import assert_equal, assert_is_instance
from collections import Iterator

from werkzeug.wrappers import Request

from rouver.response import respond_with_html, see_other

from rouver_test.util import StartResponse, default_environment


class RespondWithHTMLTest(TestCase):

    def test_default_status(self) -> None:
        sr = StartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_status(HTTPStatus.OK)

    def test_custom_status(self) -> None:
        sr = StartResponse()
        respond_with_html(
            sr, "<div>Test</div>", status=HTTPStatus.NOT_ACCEPTABLE)
        sr.assert_status(HTTPStatus.NOT_ACCEPTABLE)

    def test_content_type(self) -> None:
        sr = StartResponse()
        respond_with_html(sr, "<div>Test</div>")
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")

    def test_return_value(self) -> None:
        sr = StartResponse()
        response = respond_with_html(sr, "<div>Test</div>")
        assert_equal(b"<div>Test</div>", b"".join(response))

    def test_return_value_is_iterator(self) -> None:
        sr = StartResponse()
        response = respond_with_html(sr, "<div>Test</div>")
        assert_is_instance(response, Iterator)

    def test_return_value_encoding(self) -> None:
        sr = StartResponse()
        response = respond_with_html(sr, "<div>Täst</div>")
        assert_equal("<div>Täst</div>".encode("utf-8"), b"".join(response))

    def test_additional_headers(self) -> None:
        sr = StartResponse()
        respond_with_html(sr, "<div>Täst</div>", extra_headers=[
            ("X-Custom-Header", "Foobar"),
        ])
        sr.assert_header_equals("X-Custom-Header", "Foobar")


class SeeOtherTest(TestCase):

    def setUp(self) -> None:
        self.environment = default_environment()
        self.start_request = StartResponse()

    def test_headers(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        see_other(request, self.start_request, "/foo/bar")
        self.start_request.assert_status(HTTPStatus.SEE_OTHER)
        self.start_request.assert_header_equals(
            "Content-Type", "text/html; charset=utf-8")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_url_without_leading_slash(self) -> None:
        self.environment["SERVER_NAME"] = "www.example.com"
        request = Request(self.environment)
        see_other(request, self.start_request, "foo/bar")
        self.start_request.assert_header_equals(
            "Location", "http://www.example.com/foo/bar")

    def test_html(self) -> None:
        request = Request(self.environment)
        response = see_other(request, self.start_request, "foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")

    def test_return_value_is_iterator(self) -> None:
        request = Request(self.environment)
        response = see_other(request, self.start_request, "foo/bar")
        assert_is_instance(response, Iterator)
