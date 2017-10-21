from http import HTTPStatus
from unittest import TestCase

from asserts import assert_equal

from rouver.response import respond_with_html

from rouver_test.util import StartResponse


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

    def test_return_value_encoding(self) -> None:
        sr = StartResponse()
        response = respond_with_html(sr, "<div>Täst</div>")
        assert_equal("<div>Täst</div>".encode("utf-8"), b"".join(response))

    def test_additional_headers(self) -> None:
        sr = StartResponse()
        response = respond_with_html(sr, "<div>Täst</div>", extra_headers=[
            ("X-Custom-Header", "Foobar"),
        ])
        sr.assert_header_equals("X-Custom-Header", "Foobar")
