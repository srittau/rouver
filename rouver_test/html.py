from http import HTTPStatus
from unittest import TestCase

from asserts import assert_equal, assert_raises, assert_in

from rouver.html import http_status_page, bad_arguments_list, created_at_page, \
    temporary_redirect_page, see_other_page


class HTTPStatusPageTest(TestCase):
    def test_default(self) -> None:
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

    def test_message_and_html_message(self) -> None:
        with assert_raises(ValueError):
            http_status_page(
                HTTPStatus.NOT_ACCEPTABLE,
                message="Test",
                html_message="HTML Test")

    def test_message(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, message="Test <em>message</em>.")
        assert_equal("""<!DOCTYPE html>
<html>
    <head>
        <title>406 &mdash; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &mdash; Not Acceptable</h1>
        <p>Test &lt;em&gt;message&lt;/em&gt;.</p>
    </body>
</html>
""", html)

    def test_html_message(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, html_message="Test <em>message</em>.")
        assert_equal("""<!DOCTYPE html>
<html>
    <head>
        <title>406 &mdash; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &mdash; Not Acceptable</h1>
        <p>Test <em>message</em>.</p>
    </body>
</html>
""", html)

    def test_html_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, html_content="<div>Test content.</div>")
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

    def test_html_message_and_html_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE,
            html_message="Test message.",
            html_content="<div>Test content.</div>")
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


class CreatedAtPageTest(TestCase):
    def test_encode_url(self) -> None:
        page = created_at_page('/foo/"bar"')
        assert_in('<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>',
                  page)


class TemporaryRedirectPageTest(TestCase):
    def test_encode_url(self) -> None:
        page = temporary_redirect_page('/foo/"bar"')
        assert_in('<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>',
                  page)


class SeeOtherPageTest(TestCase):
    def test_encode_url(self) -> None:
        page = see_other_page('/foo/"bar"')
        assert_in('<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>',
                  page)


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

    def test_escape_html(self) -> None:
        html = bad_arguments_list({
            "a<c": "d<f",
        })
        assert_equal("""<ul class="bad-arguments">
    <li class="argument">
        <span class="argument-name">a&lt;c</span>:
        <span class="error-message">d&lt;f</span>
    </li>
</ul>
""", html)
