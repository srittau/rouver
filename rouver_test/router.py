from http import HTTPStatus
import logging
from typing import Iterable, List, Any
from unittest import TestCase

from asserts import assert_equal, assert_raises, assert_is_instance

from werkzeug.exceptions import Conflict
from werkzeug.wrappers import Request

from rouver.router import Router, LOGGER_NAME
from rouver.types import StartResponseType

from rouver_test.util import StartResponse, default_environment


def handle_success(_, __, start_response: StartResponseType) \
        -> Iterable[bytes]:
    start_response("200 OK", [])
    return [b""]


def handle_empty_path(_, path: List[str], start_response: StartResponseType) \
        -> Iterable[bytes]:
    assert_equal([], path)
    start_response("200 OK", [])
    return [b""]


def fail_if_called(_, __, ___) -> Iterable[bytes]:
    raise AssertionError("handler should not be called")


class RouterTest(TestCase):

    def setUp(self) -> None:
        self.router = Router()
        self.router.error_handling = False
        self.start_response = StartResponse()
        self.environment = default_environment()
        self.disable_logger()

    def disable_logger(self) -> None:
        logging.getLogger(LOGGER_NAME).disabled = True

    def handle_wsgi(self, method: str = "GET", path: str = "/") \
            -> Iterable[bytes]:
        self.environment["REQUEST_METHOD"] = method
        self.environment["PATH_INFO"] = path
        return self.router(self.environment, self.start_response)

    def test_no_routes(self) -> None:
        response = self.handle_wsgi("GET", "/foo/bar")
        self.start_response.assert_status(HTTPStatus.NOT_FOUND)
        self.start_response.assert_header_equals(
            "Content-Type", "text/html; charset=utf-8")
        html = b"".join(response).decode("utf-8")
        assert_equal("""<!DOCTYPE html>
<html>
    <head>
        <title>404 &mdash; Not Found</title>
    </head>
    <body>
        <h1>404 &mdash; Not Found</h1>
        <p>Path '/foo/bar' not found.</p>
    </body>
</html>
""", html)

    def test_handler_request(self) -> None:
        def handle(request: Request, _, start_response):
            assert_equal("test.example.com", request.host)
            start_response("200 OK", [])
            return [b""]

        self.router.add_routes([
            ("", "GET", handle),
        ])
        self.environment["SERVER_NAME"] = "test.example.com"
        self.handle_wsgi("GET", "")
        self.start_response.assert_status(HTTPStatus.OK)

    def test_empty_route(self) -> None:
        self.router.add_routes([
            ("", "GET", handle_empty_path),
        ])
        self.handle_wsgi("GET", "")
        self.start_response.assert_status(HTTPStatus.OK)

    def test_root_route(self) -> None:
        self.router.add_routes([
            ("", "GET", handle_empty_path),
        ])
        self.handle_wsgi("GET", "/")
        self.start_response.assert_status(HTTPStatus.OK)

    def test_first_level(self) -> None:
        self.router.add_routes([
            ("foo", "GET", handle_empty_path),
        ])
        self.handle_wsgi("GET", "/foo")
        self.start_response.assert_status(HTTPStatus.OK)

    def test_first_level_wrong_path(self) -> None:
        self.router.add_routes([
            ("foo", "GET", handle_empty_path),
        ])
        self.handle_wsgi("GET", "/bar")
        self.start_response.assert_status(HTTPStatus.NOT_FOUND)

    def test_level_mismatch_1(self) -> None:
        self.router.add_routes([
            ("foo/bar", "GET", handle_empty_path),
        ])
        self.handle_wsgi("GET", "/foo")
        self.start_response.assert_status(HTTPStatus.NOT_FOUND)

    def test_level_mismatch_2(self) -> None:
        self.router.add_routes([
            ("foo", "GET", handle_empty_path),
        ])
        self.handle_wsgi("GET", "/foo/bar")
        self.start_response.assert_status(HTTPStatus.NOT_FOUND)

    # Method Handling

    def test_wrong_method(self) -> None:
        self.router.add_routes([
            ("foo", "GET", fail_if_called),
            ("foo", "PUT", fail_if_called),
        ])
        self.handle_wsgi("POST", "/foo")
        self.start_response.assert_status(HTTPStatus.METHOD_NOT_ALLOWED)
        self.start_response.assert_header_equals("Allow", "GET, PUT")

    def test_call_right_method(self) -> None:
        self.router.add_routes([
            ("foo", "GET", fail_if_called),
            ("foo", "POST", handle_success),
            ("foo", "PUT", fail_if_called),
        ])
        self.handle_wsgi("POST", "/foo")
        self.start_response.assert_status(HTTPStatus.OK)

    # Path Templates

    def test_unknown_template(self) -> None:
        self.router.add_routes([
            ("foo/{unknown}/bar", "GET", fail_if_called),
        ])
        with assert_raises(KeyError):
            self.handle_wsgi("GET", "/foo/xyz/bar")

    def test_template(self) -> None:
        def handle(_, path, start_response):
            assert_equal(["xyzxyz"], path)
            start_response("200 OK", [])
            return [b""]

        def handle_path(request: Request, paths: List[Any], path: str) -> str:
            assert_is_instance(request, Request)
            assert_equal([], paths)
            return path * 2
        self.router.add_template_handler("handler", handle_path)

        self.router.add_routes([
            ("foo/{handler}/bar", "GET", handle),
        ])
        self.handle_wsgi("GET", "/foo/xyz/bar")
        self.start_response.assert_status(HTTPStatus.OK)

    def test_multiple_templates(self) -> None:
        def handle(_, path, start_response):
            assert_equal(["xyz", 123], path)
            start_response("200 OK", [])
            return [b""]

        def handle_path(_, paths: List[Any], __) -> int:
            assert_equal(["xyz"], paths)
            return 123
        self.router.add_template_handler("handler1", lambda _, __, ___: "xyz")
        self.router.add_template_handler("handler2", handle_path)

        self.router.add_routes([
            ("foo/{handler1}/bar/{handler2}", "GET", handle),
        ])
        self.handle_wsgi("GET", "/foo/xyz/bar/abc")
        self.start_response.assert_status(HTTPStatus.OK)

    def test_template_value_error(self) -> None:
        def raise_value_error(_, __, ___):
            raise ValueError()
        self.router.add_template_handler("handler", raise_value_error)

        self.router.add_routes([
            ("foo/{handler}/bar", "GET", fail_if_called),
        ])
        self.handle_wsgi("GET", "/foo/xyz/bar")
        self.start_response.assert_status(HTTPStatus.NOT_FOUND)

    def test_template_call_once_per_value(self) -> None:
        calls = 0

        def increase_count(_, __, ___):
            nonlocal calls
            calls += 1
        self.router.add_template_handler("handler", increase_count)

        self.router.add_routes([
            ("foo/{handler}/bar", "GET", fail_if_called),
            ("foo/{handler}/baz", "GET", handle_success),
        ])
        self.handle_wsgi("GET", "/foo/xyz/baz")
        assert_equal(1, calls)

    def test_template_call_twice_for_differing_values(self) -> None:
        calls = 0

        def increase_count(_, __, ___):
            nonlocal calls
            calls += 1
        self.router.add_template_handler("handler", increase_count)

        self.router.add_routes([
            ("foo/{handler}/bar", "GET", fail_if_called),
            ("foo/xyz/{handler}", "GET", handle_success),
        ])
        self.handle_wsgi("GET", "/foo/xyz/baz")
        assert_equal(2, calls)

    # Error Handling

    def test_template_key_error_with_error_handling(self) -> None:
        def raise_key_error(_, __, ___):
            raise KeyError()
        self.router.add_template_handler("handler", raise_key_error)

        self.router.add_routes([
            ("foo/{handler}/bar", "GET", fail_if_called),
        ])
        self.router.error_handling = True
        self.handle_wsgi("GET", "/foo/xyz/bar")
        self.start_response.assert_status(HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_template_key_error_without_error_handling(self) -> None:
        def raise_key_error(_, __, ___):
            raise KeyError()
        self.router.add_template_handler("handler", raise_key_error)

        self.router.add_routes([
            ("foo/{handler}/bar", "GET", fail_if_called),
        ])
        self.router.error_handling = False
        with assert_raises(KeyError):
            self.handle_wsgi("GET", "/foo/xyz/bar")

    def test_handler_key_error_with_error_handling(self) -> None:
        def handle(_, __, ___):
            raise KeyError()

        self.router.error_handling = True
        self.router.add_routes([
            ("foo", "GET", handle),
        ])
        self.handle_wsgi("GET", "/foo")
        self.start_response.assert_status(HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_handler_key_error_without_error_handling(self) -> None:
        def handle(_, __, ___):
            raise KeyError()

        self.router.add_routes([
            ("foo", "GET", handle),
        ])
        self.router.error_handling = False
        with assert_raises(KeyError):
            self.handle_wsgi("GET", "/foo")

    def test_http_error(self) -> None:
        def handle(_, __, ___):
            raise Conflict()

        self.router.error_handling = False
        self.router.add_routes([
            ("foo", "GET", handle),
        ])
        response = self.handle_wsgi("GET", "/foo")
        self.start_response.assert_status(HTTPStatus.CONFLICT)
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
