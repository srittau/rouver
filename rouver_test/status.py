from http import HTTPStatus

from asserts import assert_equal
from dectest import TestCase, test

from rouver.status import status_line


class StatusLineTest(TestCase):
    @test
    def status_line(self) -> None:
        sl = status_line(HTTPStatus.NO_CONTENT)
        assert_equal("204 No Content", sl)
