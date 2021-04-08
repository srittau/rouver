from __future__ import annotations

import re
from collections.abc import Iterable
from http import HTTPStatus
from io import BytesIO, StringIO
from typing import Any

from asserts import assert_equal, assert_false, assert_regex, assert_true

from rouver.types import Header, StartResponseReturnType, WSGIEnvironment

_status_re = re.compile(r"^(\d\d\d) (.*)$")


class TestingStartResponse:
    def __init__(self) -> None:
        self.was_called = False
        self.status = ""
        self.headers: list[Header] = []

    def __call__(
        self, status: str, headers: Iterable[Header], exc_info: Any = None
    ) -> StartResponseReturnType:
        assert_false(self.was_called, "start_response() called twice")
        assert_regex(status, _status_re)
        self.was_called = True
        self.status = status
        self.headers = list(headers)
        return lambda s: None

    @property
    def status_code(self) -> int:
        self.assert_was_called()
        assert len(self.status) >= 3
        return int(self.status[:3])

    def assert_was_called(self) -> None:
        assert_true(self.was_called, "start_response() was not called")

    def assert_status(self, status: HTTPStatus) -> None:
        assert_equal(status.value, self.status_code)

    def assert_header_missing(self, name: str) -> None:
        value = self._find_header(name)
        if value is not None:
            raise AssertionError("header {} unexpectedly found".format(name))

    def assert_header_equals(self, name: str, value: str) -> None:
        header_value = self._find_header(name)
        if header_value is None:
            raise AssertionError("missing header '{}'".format(name))
        assert_equal(
            value,
            header_value,
            "'{}': '{}' != '{}".format(name, value, header_value),
        )

    def _find_header(self, name: str) -> str | None:
        self.assert_was_called()
        found = None
        for (header_name, header_value) in self.headers:
            if header_name.lower() == name.lower():
                if not isinstance(header_value, str):
                    raise AssertionError("invalue header value")
                if found is not None:
                    raise AssertionError(
                        "duplicate header '{}'".format(header_name)
                    )
                found = header_value
        return found


def default_environment() -> WSGIEnvironment:
    return {
        "REQUEST_METHOD": "GET",
        "SERVER_NAME": "www.example.com",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(b""),
        "wsgi.errors": StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
