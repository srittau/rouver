from http import HTTPStatus
from unittest import TestCase

from asserts import assert_equal

from rouver.html import http_status_page, bad_arguments_list


class HTTPStatusPageTest(TestCase):

    def test_http_status_page_default(self) -> None:
        html = http_status_page(HTTPStatus.NOT_ACCEPTABLE)
        assert_equal("""<!DOCTYPE html>
<html>
    <head>
        <title>406 &mdash; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &mdash; Not Acceptable</h1>
    </body>
</html>
""", html)

    def test_http_status_page_with_message(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, message="Test message.")
        assert_equal("""<!DOCTYPE html>
<html>
    <head>
        <title>406 &mdash; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &mdash; Not Acceptable</h1>
        <p>Test message.</p>
    </body>
</html>
""", html)

    def test_http_status_page_with_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, content="<div>Test content.</div>")
        assert_equal("""<!DOCTYPE html>
<html>
    <head>
        <title>406 &mdash; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &mdash; Not Acceptable</h1>
<div>Test content.</div>
    </body>
</html>
""", html)

    def test_http_status_page_with_message_and_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, message="Test message.",
            content="<div>Test content.</div>")
        assert_equal("""<!DOCTYPE html>
<html>
    <head>
        <title>406 &mdash; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &mdash; Not Acceptable</h1>
        <p>Test message.</p>
<div>Test content.</div>
    </body>
</html>
""", html)


class BadArgumentsListTest(TestCase):

    def test_empty_dict(self) -> None:
        html = bad_arguments_list({})
        assert_equal("", html)

    def test_one_item(self) -> None:
        html = bad_arguments_list({"foo": "bar"})
        assert_equal("""<ul class="bad-arguments">
    <li class="argument">
        <span class="argument-name">foo</span>:
        <span class="error-message">bar</span>
    </li>
</ul>
""", html)

    def test_multiple_items_alphabetically(self) -> None:
        html = bad_arguments_list({
            "def": "error 1",
            "abc": "error 2",
            "ghi": "error 3",
        })
        assert_equal("""<ul class="bad-arguments">
    <li class="argument">
        <span class="argument-name">abc</span>:
        <span class="error-message">error 2</span>
    </li>
    <li class="argument">
        <span class="argument-name">def</span>:
        <span class="error-message">error 1</span>
    </li>
    <li class="argument">
        <span class="argument-name">ghi</span>:
        <span class="error-message">error 3</span>
    </li>
</ul>
""", html)
