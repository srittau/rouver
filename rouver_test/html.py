from http import HTTPStatus
from unittest import TestCase

from asserts import assert_equal

from rouver.html import http_status_page


class HTTPStatusPageTest(TestCase):

    def test_http_status_page(self) -> None:
        html = http_status_page(HTTPStatus.NOT_ACCEPTABLE, "Test message.")
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
