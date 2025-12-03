from http import HTTPStatus

from rouver.status import status_line


class TestStatusLine:
    def test_status_line(self) -> None:
        sl = status_line(HTTPStatus.NO_CONTENT)
        assert sl == "204 No Content"
