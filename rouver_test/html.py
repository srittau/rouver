from http import HTTPStatus

import pytest

from rouver.html import (
    bad_arguments_list,
    created_at_page,
    http_status_page,
    see_other_page,
    temporary_redirect_page,
)


class TestHTTPStatusPage:
    def test_default(self) -> None:
        html = http_status_page(HTTPStatus.NOT_ACCEPTABLE)
        assert html == (
            """<!DOCTYPE html>
<html>
    <head>
        <title>406 &#x2014; Not Acceptable</title>
    </head>
    <body>
        <h1>406 &#x2014; Not Acceptable</h1>
    </body>
</html>
"""
        )

    def test_message_and_html_message(self) -> None:
        with pytest.raises(ValueError):
            http_status_page(
                HTTPStatus.NOT_ACCEPTABLE,
                message="Test",
                html_message="HTML Test",
            )

    def test_message(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, message="Test <em>message</em>."
        )
        assert html == (
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
"""
        )

    def test_html_message(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, html_message="Test <em>message</em>."
        )
        assert html == (
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
"""
        )

    def test_html_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE, html_content="<div>Test content.</div>"
        )
        assert html == (
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
"""
        )

    def test_html_message_and_html_content(self) -> None:
        html = http_status_page(
            HTTPStatus.NOT_ACCEPTABLE,
            html_message="Test message.",
            html_content="<div>Test content.</div>",
        )
        assert html == (
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
"""
        )


class TestCreatedAtPage:
    def test_encode_url(self) -> None:
        page = created_at_page('/foo/"bar"')
        assert (
            '<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>' in page
        )


class TestTemporaryRedirectPage:
    def test_encode_url(self) -> None:
        page = temporary_redirect_page('/foo/"bar"')
        assert (
            '<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>' in page
        )


class TestSeeOtherPage:
    def test_encode_url(self) -> None:
        page = see_other_page('/foo/"bar"')
        assert (
            '<a href="/foo/&quot;bar&quot;">/foo/&quot;bar&quot;</a>' in page
        )


class TestBadArgumentsList:
    def test_empty_dict(self) -> None:
        html = bad_arguments_list({})
        assert html == ""

    def test_one_item(self) -> None:
        html = bad_arguments_list({"foo": "bar"})
        assert html == (
            """<ul class="bad-arguments">
    <li class="argument">
        <span class="argument-name">foo</span>:
        <span class="error-message">bar</span>
    </li>
</ul>
"""
        )

    def test_multiple_items_alphabetically(self) -> None:
        html = bad_arguments_list(
            {"def": "error 1", "abc": "error 2", "ghi": "error 3"}
        )
        assert html == (
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
"""
        )

    def test_escape_html(self) -> None:
        html = bad_arguments_list({"a<c": "d<f"})
        assert html == (
            """<ul class="bad-arguments">
    <li class="argument">
        <span class="argument-name">a&lt;c</span>:
        <span class="error-message">d&lt;f</span>
    </li>
</ul>
"""
        )
