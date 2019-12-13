from http import HTTPStatus

from asserts import assert_equal, assert_in, assert_raises
from dectest import TestCase, test

from rouver.html import (
    bad_arguments_list,
    created_at_page,
    http_status_page,
    see_other_page,
    temporary_redirect_page,
)


class HTTPStatusPageTest(TestCase):
    @test
    def default(self) -> None:
        html = http_status_page(HTTPStatus.NOT_ACCEPTABLE)
        assert_equal(
            """<!DOCTYPE html>
<html>
    <head>
        <title>406 &#x2014; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &#x2014; Not Acceptable</h1>
    </body>
</html>
""",
            html,
        )

    @test
    def message_and_html_message(self) -> None:
        with assert_raises(ValueError):
            http_status_page(
                HTTPStatus.NOT_ACCEPTABLE,
                message="Test",
                html_message="HTML Test",
            )

    @test
    def message(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, message="Test <em>message</em>."
        )
        assert_equal(
            """<!DOCTYPE html>
<html>
    <head>
        <title>406 &#x2014; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &#x2014; Not Acceptable</h1>
        <p>Test &lt;em&gt;message&lt;/em&gt;.</p>
    </body>
</html>
""",
            html,
        )

    @test
    def html_message(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, html_message="Test <em>message</em>."
        )
        assert_equal(
            """<!DOCTYPE html>
<html>
    <head>
        <title>406 &#x2014; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &#x2014; Not Acceptable</h1>
        <p>Test <em>message</em>.</p>
    </body>
</html>
""",
            html,
        )

    @test
    def html_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, html_content="<div>Test content.</div>"
        )
        assert_equal(
            """<!DOCTYPE html>
<html>
    <head>
        <title>406 &#x2014; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &#x2014; Not Acceptable</h1>
<div>Test content.</div>
    </body>
</html>
""",
            html,
        )

    @test
    def html_message_and_html_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE,
            html_message="Test message.",
            html_content="<div>Test content.</div>",
        )
        assert_equal(
            """<!DOCTYPE html>
<html>
    <head>
        <title>406 &#x2014; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &#x2014; Not Acceptable</h1>
        <p>Test message.</p>
<div>Test content.</div>
    </body>
</html>
""",
            html,
        )


class CreatedAtPageTest(TestCase):
    @test
    def encode_url(self) -> None:
        page = created_at_page('/foo/"bar"')
        assert_in(
            '<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>', page
        )


class TemporaryRedirectPageTest(TestCase):
    @test
    def encode_url(self) -> None:
        page = temporary_redirect_page('/foo/"bar"')
        assert_in(
            '<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>', page
        )


class SeeOtherPageTest(TestCase):
    @test
    def encode_url(self) -> None:
        page = see_other_page('/foo/"bar"')
        assert_in(
            '<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>', page
        )


class BadArgumentsListTest(TestCase):
    @test
    def empty_dict(self) -> None:
        html = bad_arguments_list({})
        assert_equal("", html)

    @test
    def one_item(self) -> None:
        html = bad_arguments_list({"foo": "bar"})
        assert_equal(
            """<ul class="bad-arguments">
    <li class="argument">
        <span class="argument-name">foo</span>:
        <span class="error-message">bar</span>
    </li>
</ul>
""",
            html,
        )

    @test
    def multiple_items_alphabetically(self) -> None:
        html = bad_arguments_list(
            {"def": "error 1", "abc": "error 2", "ghi": "error 3"}
        )
        assert_equal(
            """<ul class="bad-arguments">
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
""",
            html,
        )

    @test
    def escape_html(self) -> None:
        html = bad_arguments_list({"a<c": "d<f"})
        assert_equal(
            """<ul class="bad-arguments">
    <li class="argument">
        <span class="argument-name">a&lt;c</span>:
        <span class="error-message">d&lt;f</span>
    </li>
</ul>
""",
            html,
        )
