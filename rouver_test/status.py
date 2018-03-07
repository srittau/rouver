from http import HTTPStatus

from unittest import TestCase

from asserts import assert_equal

from rouver.status import status_line


class StatusLineTest(TestCase):
    def test_status_line(self) -> None:
        sl = status_line(HTTPStatus.NO_CONTENT)
        assert_equal("204 No Content", sl)
