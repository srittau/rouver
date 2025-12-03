from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from http import HTTPStatus

import pytest
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import Unauthorized
from werkzeug.wrappers import Request

from rouver.exceptions import ArgumentsError
from rouver.router import LOGGER_NAME, Router
from rouver.types import (
    StartResponse,
    WSGIApplication,
    WSGIEnvironment,
    WSGIResponse,
)
from rouver_test.testutil import StubStartResponse, default_environment


def handle_success(
    _: WSGIEnvironment, start_response: StartResponse
) -> Iterable[bytes]:
    start_response("200 OK", [])
    return [b""]


def handle_empty_path(
    environ: WSGIEnvironment, start_response: StartResponse
) -> Iterable[bytes]:
    assert environ["rouver.path_args"] == []
    start_response("200 OK", [])
    return [b""]


def fail_if_called(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
    raise AssertionError("handler should not be called")


@pytest.fixture(autouse=True)
def disable_logging() -> Iterable[None]:
    logging.getLogger(LOGGER_NAME).disabled = True
    yield
    logging.getLogger(LOGGER_NAME).disabled = False


def setup_router() -> Router:
    router = Router()
    router.error_handling = False
    return router


class TestRouter:
    def _create_path_checker(self, expected_path: str) -> WSGIApplication:
        def handle(
            environ: WSGIEnvironment, sr: StartResponse
        ) -> Sequence[bytes]:
            assert environ["PATH_INFO"] == expected_path
            sr("200 OK", [])
            return []

        return handle

    def handle_wsgi(
        self,
        router: Router,
        env: WSGIEnvironment,
        method: str = "GET",
        path: str = "/",
        st: StubStartResponse | None = None,
        *,
        script_name: str = "",
    ) -> Iterable[bytes]:
        if st is None:
            st = StubStartResponse()
        env["REQUEST_METHOD"] = method
        env["PATH_INFO"] = path
        env["SCRIPT_NAME"] = script_name
        return router(env, st)

    def test_not_found_response_page(self) -> None:
        env = default_environment()
        response = self.handle_wsgi(setup_router(), env, "GET", "/foo/bar")
        html = b"".join(response).decode("utf-8")
        assert html == (
            """<!DOCTYPE html>
<html>
    <head>
        <title>404 &#x2014; Not Found</title>
    </head>
    <body>
        <h1>404 &#x2014; Not Found</h1>
        <p>Path &#x27;/foo/bar&#x27; not found.</p>
    </body>
</html>
"""
        )

    def test_not_found_escape_path(self) -> None:
        env = default_environment()
        response = self.handle_wsgi(setup_router(), env, "GET", "/foo/<bar")
        html = b"".join(response).decode("utf-8")
        assert "<p>Path &#x27;/foo/&lt;bar&#x27; not found.</p>" in html

    def test_no_routes(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(setup_router(), env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")

    def test_handler_request(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["SERVER_NAME"] == "test.example.com"
            start_response("200 OK", [])
            return [b""]

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()
        router.add_routes([("", "GET", handle)])
        env["SERVER_NAME"] = "test.example.com"
        self.handle_wsgi(router, env, "GET", "", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_empty_route(self) -> None:
        router = setup_router()
        router.add_routes([("", "GET", handle_empty_path)])
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_root_route(self) -> None:
        router = setup_router()
        router.add_routes([("", "GET", handle_empty_path)])
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_first_level(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.wildcard_path"] == ""
            start_response("200 OK", [])
            return []

        env = default_environment()
        sr = StubStartResponse()
        router = setup_router()
        router.add_routes([("foo", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_first_level__trailing_slash(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.wildcard_path"] == "/"
            start_response("200 OK", [])
            return []

        env = default_environment()
        sr = StubStartResponse()
        router = setup_router()
        router.add_routes([("foo", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_first_level_wrong_path(self) -> None:
        router = setup_router()
        router.add_routes([("foo", "GET", handle_empty_path)])
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/bar", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_level_mismatch_1(self) -> None:
        sr = StubStartResponse()
        router = setup_router()
        router.add_routes([("foo/bar", "GET", handle_empty_path)])
        env = default_environment()
        self.handle_wsgi(router, env, "GET", "/foo", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_level_mismatch_2(self) -> None:
        sr = StubStartResponse()
        router = setup_router()
        router.add_routes([("foo", "GET", handle_empty_path)])
        env = default_environment()
        self.handle_wsgi(router, env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_decode_path(self) -> None:
        sr = StubStartResponse()
        router = setup_router()
        router.add_routes([("foo/bär", "GET", handle_success)])
        env = default_environment()
        self.handle_wsgi(router, env, "GET", "/foo/b%c3%a4r", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_invalid_path_encoding(self) -> None:
        sr = StubStartResponse()
        router = setup_router()
        router.add_routes([("foo/bar", "GET", handle_success)])
        env = default_environment()
        self.handle_wsgi(router, env, "GET", "/foo/b%c3r", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    # Method Handling

    def test_wrong_method_response_page(self) -> None:
        router = setup_router()
        env = default_environment()
        router.add_routes(
            [("foo", "GET", fail_if_called), ("foo", "PUT", fail_if_called)]
        )
        response = self.handle_wsgi(router, env, "POST", "/foo")
        html = b"".join(response).decode("utf-8")
        assert html == (
            """<!DOCTYPE html>
<html>
    <head>
        <title>405 &#x2014; Method Not Allowed</title>
    </head>
    <body>
        <h1>405 &#x2014; Method Not Allowed</h1>
        <p>Method &#x27;POST&#x27; not allowed. Please try GET or PUT.</p>
    </body>
</html>
"""
        )

    def test_wrong_method_escape_method(self) -> None:
        env = default_environment()
        router = setup_router()
        router.add_routes([("foo", "GET", fail_if_called)])
        response = self.handle_wsgi(router, env, "G<T", "/foo")
        html = b"".join(response).decode("utf-8")
        assert (
            "<p>Method &#x27;G&lt;T&#x27; not allowed. Please try GET.</p>"
            in html
        )

    def test_wrong_method(self) -> None:
        router = setup_router()
        router.add_routes(
            [("foo", "GET", fail_if_called), ("foo", "PUT", fail_if_called)]
        )
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "POST", "/foo", sr)
        sr.assert_status(HTTPStatus.METHOD_NOT_ALLOWED)
        sr.assert_header_equals("Allow", "GET, PUT")

    def test_wrong_method__multiple_matches(self) -> None:
        router = setup_router()
        router.add_routes(
            [("foo", "GET", fail_if_called), ("foo", "GET", fail_if_called)]
        )
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "POST", "/foo", sr)
        sr.assert_status(HTTPStatus.METHOD_NOT_ALLOWED)
        sr.assert_header_equals("Allow", "GET")

    def test_call_right_method(self) -> None:
        router = setup_router()
        env = default_environment()
        sr = StubStartResponse()
        router.add_routes(
            [
                ("foo", "GET", fail_if_called),
                ("foo", "POST", handle_success),
                ("foo", "PUT", fail_if_called),
            ]
        )
        self.handle_wsgi(router, env, "POST", "/foo", sr)
        sr.assert_status(HTTPStatus.OK)

    # Path Templates

    def test_unknown_template(self) -> None:
        router = setup_router()
        with pytest.raises(KeyError):
            router.add_routes([("foo/{unknown}/bar", "GET", fail_if_called)])

    def test_no_template(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == []
            start_response("200 OK", [])
            return [b""]

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()
        router.add_routes([("foo/bar", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_template(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == ["xyzxyz"]
            start_response("200 OK", [])
            return [b""]

        def handle_path(
            request: Request, paths: tuple[object, ...], path: str
        ) -> str:
            assert isinstance(request, Request)
            assert paths == ()
            return path * 2

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()

        router.add_template_handler("handler", handle_path)

        router.add_routes([("foo/{handler}/bar", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/xyz/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_multiple_templates(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == ["xyz", 123]
            start_response("200 OK", [])
            return [b""]

        def handle_path(_: Request, paths: tuple[object, ...], __: str) -> int:
            assert paths == ("xyz",)
            return 123

        env = default_environment()
        sr = StubStartResponse()

        router = setup_router()
        router.add_template_handler("handler1", lambda _, __, ___: "xyz")
        router.add_template_handler("handler2", handle_path)

        router.add_routes([("foo/{handler1}/bar/{handler2}", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/xyz/bar/abc", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_template_handler_is_passed_decoded_value(self) -> None:
        def handle_path(_: Request, __: object, v: str) -> None:
            assert v == "foo/bar"

        env = default_environment()

        router = setup_router()
        router.add_template_handler("handler", handle_path)
        sr = StubStartResponse()

        router.add_routes([("foo/{handler}", "GET", handle_success)])
        self.handle_wsgi(router, env, "GET", "/foo/foo%2Fbar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_template_handler_is_not_passed_an_invalid_value(self) -> None:
        def handle_path(_: Request, __: object, v: str) -> None:
            pytest.fail("template handler should not have been called")

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()

        router.add_template_handler("handler", handle_path)
        router.add_routes([("foo/{handler}", "GET", handle_success)])
        self.handle_wsgi(router, env, "GET", "/foo/foo%C3bar", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_template_value_error(self) -> None:
        def raise_value_error(_: Request, __: Sequence[str], ___: str) -> None:
            raise ValueError()

        env = default_environment()
        sr = StubStartResponse()
        router = setup_router()

        router.add_template_handler("handler", raise_value_error)

        router.add_routes([("foo/{handler}/bar", "GET", fail_if_called)])
        self.handle_wsgi(router, env, "GET", "/foo/xyz/bar", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_template_multiple_matches(self) -> None:
        def raise_value_error(_: Request, __: Sequence[str], ___: str) -> None:
            raise ValueError()

        env = default_environment()
        sr = StubStartResponse()
        router = setup_router()

        router.add_template_handler("handler1", raise_value_error)
        router.add_template_handler("handler2", lambda _, __, ___: None)

        router.add_routes(
            [
                ("foo/{handler1}/bar", "GET", fail_if_called),
                ("foo/{handler2}/bar", "GET", handle_success),
            ]
        )
        self.handle_wsgi(router, env, "GET", "/foo/xyz/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_template_multiple_matches__match_first(self) -> None:
        env = default_environment()
        sr = StubStartResponse()
        router = setup_router()

        router.add_template_handler("handler1", lambda _, __, ___: None)
        router.add_template_handler("handler2", lambda _, __, ___: None)

        router.add_routes(
            [
                ("foo/{handler1}/bar", "GET", handle_success),
                ("foo/{handler2}/bar", "GET", fail_if_called),
            ]
        )
        self.handle_wsgi(router, env, "GET", "/foo/xyz/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_template_call_once_per_value(self) -> None:
        calls = 0

        def increase_count(_: Request, __: Sequence[str], ___: str) -> None:
            nonlocal calls
            calls += 1

        env = default_environment()
        router = setup_router()

        router.add_template_handler("handler", increase_count)

        router.add_routes(
            [
                ("foo/{handler}/bar", "GET", fail_if_called),
                ("foo/{handler}/baz", "GET", handle_success),
            ]
        )
        self.handle_wsgi(router, env, "GET", "/foo/xyz/baz")
        assert calls == 1

    def test_template_call_twice_for_differing_values(self) -> None:
        calls = 0

        def increase_count(_: Request, __: Sequence[str], ___: str) -> None:
            nonlocal calls
            calls += 1

        env = default_environment()
        router = setup_router()

        router.add_template_handler("handler", increase_count)

        router.add_routes(
            [
                ("foo/{handler}/bar", "GET", fail_if_called),
                ("foo/xyz/{handler}", "GET", handle_success),
            ]
        )
        self.handle_wsgi(router, env, "GET", "/foo/xyz/baz")
        assert calls == 2

    # Wildcard Paths

    def test_no_wildcard_path(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.wildcard_path"] == ""
            start_response("200 OK", [])
            return [b""]

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()

        router.add_routes([("foo/bar", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_wildcard_path__no_trailing_slash(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == []
            assert environ["rouver.wildcard_path"] == ""
            start_response("200 OK", [])
            return [b""]

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()

        router.add_routes([("foo/bar/*", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_wildcard_path__with_trailing_slash(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == []
            assert environ["rouver.wildcard_path"] == "/"
            start_response("200 OK", [])
            return [b""]

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()

        router.add_routes([("foo/bar/*", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/bar/", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_wildcard_path__additional_path(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == []
            assert environ["rouver.wildcard_path"] == "/abc/def"
            start_response("200 OK", [])
            return [b""]

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()
        router.add_routes([("foo/bar/*", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/bar/abc/def", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_wildcard_path__with_template(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == ["value"]
            assert environ["rouver.wildcard_path"] == "/abc/def"
            start_response("200 OK", [])
            return [b""]

        env = default_environment()
        router = setup_router()
        sr = StubStartResponse()
        router.add_template_handler("bar", lambda *args: "value")
        router.add_routes([("foo/{bar}/*", "GET", handle)])
        self.handle_wsgi(router, env, "GET", "/foo/unknown/abc/def", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_wildcard_path__too_short(self) -> None:
        router = setup_router()
        sr = StubStartResponse()
        router.add_routes([("foo/bar/*", "GET", handle_success)])
        env = default_environment()
        self.handle_wsgi(router, env, "GET", "/foo", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_wildcard_path__does_not_match(self) -> None:
        router = setup_router()
        router.add_routes([("foo/bar/*", "GET", handle_success)])
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/wrong", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_wildcard_path__not_at_end(self) -> None:
        router = setup_router()
        with pytest.raises(ValueError):
            router.add_routes([("foo/*/bar", "GET", handle_success)])

    def test_wildcard__before_more_specific(self) -> None:
        router = setup_router()
        router.add_routes(
            [
                ("foo/*", "GET", handle_success),
                ("foo/bar", "GET", fail_if_called),
            ]
        )
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_wildcard__after_more_specific(self) -> None:
        router = setup_router()
        router.add_routes(
            [
                ("foo/bar", "GET", handle_success),
                ("foo/*", "GET", fail_if_called),
            ]
        )
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    # Sub routers

    def test_sub_router(self) -> None:
        sub = Router()
        sub.error_handling = False
        sub.add_routes([("sub", "GET", self._create_path_checker("/sub"))])
        router = setup_router()
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar/sub", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__no_match(self) -> None:
        sub = Router()
        sub.error_handling = False
        sub.add_routes([("sub", "GET", fail_if_called)])
        router = setup_router()
        router.add_sub_router("foo", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/wrong/sub", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_sub_router__base_with_slash(self) -> None:
        sub = Router()
        sub.error_handling = False
        sub.add_routes([("", "GET", self._create_path_checker("/"))])
        router = setup_router()
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar/", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__base_without_slash(self) -> None:
        sub = Router()
        sub.error_handling = False
        sub.add_routes([("", "GET", self._create_path_checker(""))])
        router = setup_router()
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__path_info(self) -> None:
        def app(
            environ: WSGIEnvironment, sr: StartResponse
        ) -> Iterable[bytes]:
            assert environ["PATH_INFO"] == "/foo"
            assert environ["SCRIPT_NAME"] == "script/sub"
            assert environ["rouver.original_path_info"] == "/sub/foo"
            sr("200 OK", [])
            return []

        router = setup_router()
        env = default_environment()
        sr = StubStartResponse()
        router.error_handling = False
        router.add_sub_router("sub", app)
        self.handle_wsgi(
            router, env, "GET", "/sub/foo", sr, script_name="script"
        )
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__path_info_encoding(self) -> None:
        expected_path = "/föo".encode("utf-8").decode("latin-1")

        def app(env: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            assert env["PATH_INFO"] == expected_path
            sr("200 OK", [])
            return []

        router = setup_router()
        router.error_handling = False
        router.add_sub_router("sub", app)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(
            router,
            env,
            "GET",
            "/sub/föo".encode("utf-8").decode("latin-1"),
            sr,
        )
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__template_in_super_router(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == []
            start_response("200 OK", [])
            return []

        def tmpl(_: Request, path: Sequence[str], v: str) -> str:
            assert path == ()
            return v * 2

        env = default_environment()

        sub = Router()
        sub.error_handling = False
        sub.add_template_handler("tmpl", tmpl)
        sub.add_routes([("sub", "GET", handle)])
        router = setup_router()
        router.add_template_handler("tmpl", tmpl)
        router.add_sub_router("foo/{tmpl}", sub)
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar/sub", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__template_in_sub_router(self) -> None:
        def handle(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> Iterable[bytes]:
            assert environ["rouver.path_args"] == ["xyzxyz"]
            start_response("200 OK", [])
            return []

        def tmpl(_: Request, path: Sequence[str], v: str) -> str:
            assert path == ()
            return v * 2

        sub = Router()
        sub.error_handling = False
        sub.add_template_handler("tmpl", tmpl)
        sub.add_routes([("{tmpl}", "GET", handle)])
        router = setup_router()
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar/xyz", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__path_component(self) -> None:
        sub = Router()
        sub.error_handling = False
        sub.add_routes([("sub", "GET", handle_success)])
        router = setup_router()
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/barsub", sr)
        sr.assert_status(HTTPStatus.NOT_FOUND)

    def test_sub_router__match_after_other_routes(self) -> None:
        sub = Router()
        sub.error_handling = False
        sub.add_routes([("sub", "GET", fail_if_called)])
        router = setup_router()
        router.add_routes([("foo/bar/sub", "GET", handle_success)])
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar/sub", sr)
        sr.assert_status(HTTPStatus.OK)

    def test_sub_router__accepts_any_wsgi_app(self) -> None:
        def sub(environ: WSGIEnvironment, sr: StartResponse) -> WSGIResponse:
            assert environ["PATH_INFO"] == "/sub"
            sr("204 No Content", [])
            return []

        router = setup_router()
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/bar/sub", sr)
        sr.assert_status(HTTPStatus.NO_CONTENT)

    def test_sub_router__escaped_path(self) -> None:
        sub = Router()
        sub.error_handling = False
        sub.add_routes([("sub", "GET", self._create_path_checker("/s%75b"))])
        router = setup_router()
        router.add_sub_router("foo/bar", sub)
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/b%61r/s%75b", sr)
        sr.assert_status(HTTPStatus.OK)

    # Error Handling

    def test_internal_error_page(self) -> None:
        def handle(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            raise KeyError("Custom < error")

        router = setup_router()
        router.error_handling = True
        router.add_routes([("foo", "GET", handle)])
        env = default_environment()
        response = self.handle_wsgi(router, env, "GET", "/foo")
        html = b"".join(response).decode("utf-8")
        assert html == (
            """<!DOCTYPE html>
<html>
    <head>
        <title>500 &#x2014; Internal Server Error</title>
    </head>
    <body>
        <h1>500 &#x2014; Internal Server Error</h1>
        <p>Internal server error.</p>
    </body>
</html>
"""
        )

    def test_template_key_error_with_error_handling(self) -> None:
        def raise_key_error(_: Request, __: Sequence[str], ___: str) -> None:
            raise KeyError()

        router = setup_router()
        router.add_template_handler("handler", raise_key_error)

        router.add_routes([("foo/{handler}/bar", "GET", fail_if_called)])
        router.error_handling = True
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo/xyz/bar", sr)
        sr.assert_status(HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_template_key_error_without_error_handling(self) -> None:
        def raise_key_error(_: Request, __: Sequence[str], ___: str) -> None:
            raise KeyError()

        env = default_environment()
        router = setup_router()
        router.add_template_handler("handler", raise_key_error)

        router.add_routes([("foo/{handler}/bar", "GET", fail_if_called)])
        router.error_handling = False
        with pytest.raises(KeyError):
            self.handle_wsgi(router, env, "GET", "/foo/xyz/bar")

    def test_handler_key_error_with_error_handling(self) -> None:
        def handle(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            raise KeyError()

        router = setup_router()
        router.error_handling = True
        router.add_routes([("foo", "GET", handle)])
        env = default_environment()
        sr = StubStartResponse()
        self.handle_wsgi(router, env, "GET", "/foo", sr)
        sr.assert_status(HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_handler_key_error_without_error_handling(self) -> None:
        def handle(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            raise KeyError()

        env = default_environment()
        router = setup_router()

        router.add_routes([("foo", "GET", handle)])
        router.error_handling = False
        with pytest.raises(KeyError):
            self.handle_wsgi(router, env, "GET", "/foo")

    def test_http_error(self) -> None:
        def handle(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            raise Unauthorized(
                "Foo < Bar", www_authenticate=WWWAuthenticate("Test")
            )

        router = setup_router()
        router.error_handling = False
        router.add_routes([("foo", "GET", handle)])
        env = default_environment()
        sr = StubStartResponse()
        response = self.handle_wsgi(router, env, "GET", "/foo", sr)
        sr.assert_status(HTTPStatus.UNAUTHORIZED)
        sr.assert_header_equals("Content-Type", "text/html; charset=utf-8")
        sr.assert_header_equals("WWW-Authenticate", "Test ")
        html = b"".join(response).decode("utf-8")
        assert html == (
            """<!DOCTYPE html>
<html>
    <head>
        <title>401 &#x2014; Unauthorized</title>
    </head>
    <body>
        <h1>401 &#x2014; Unauthorized</h1>
        <p>Foo &lt; Bar</p>
    </body>
</html>
"""
        )

    def test_arguments_error(self) -> None:
        def handle(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            raise ArgumentsError({"foo": "bar"})

        router = setup_router()
        router.add_routes([("foo", "GET", handle)])
        env = default_environment()
        sr = StubStartResponse()
        response = self.handle_wsgi(router, env, "GET", "/foo", sr)
        sr.assert_status(HTTPStatus.BAD_REQUEST)
        html = b"".join(response).decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert re.search(
            r'<li class="argument">\s*'
            r'<span class="argument-name">foo</span>:\s*'
            r'<span class="error-message">bar</span>\s*'
            r"</li>",
            html,
        ), f"argument error not found in response:\n{html}"
