from __future__ import annotations

import json
import re
import secrets
from collections.abc import Callable, Iterable, Sequence
from http import HTTPStatus
from io import BytesIO
from json import JSONDecodeError
from types import TracebackType
from typing import Any, Union
from urllib.parse import quote_plus, urlparse

from dectest import TestCase, before
from werkzeug.http import parse_options_header

from rouver.args import Multiplicity
from rouver.router import Router
from rouver.types import Header, WSGIApplication, WSGIEnvironment

_STATUS_RE = re.compile(r"^(\d\d\d) [ -~]+$")


class TestRequest:
    def __init__(self, method: str, path: str) -> None:
        self.method = method.upper()
        self.path = path
        self._body = b""
        self.error_stream = BytesIO()
        self.content_type: str | None = None
        self._extra_environ: WSGIEnvironment = {}
        self._extra_headers: list[tuple[str, str]] = []
        self._arguments: list[tuple[str, str]] = []
        self._file_arguments: list[tuple[str, bytes, str, str | None]] = []
        self._boundary: str | None = None

    @property
    def body(self) -> bytes:
        return self._body

    @body.setter
    def body(self, body: bytes) -> None:
        if not isinstance(body, bytes):
            raise TypeError("body must be bytes")
        if body != b"" and self.method == "GET":
            raise ValueError("GET requests can not have a body")
        if self._arguments:
            raise ValueError(
                "setting arguments and a body is mutually exclusive"
            )
        self._body = body

    def set_json_request(
        self, body: str | bytes | dict[str, Any] | list[Any]
    ) -> None:
        """Send JSON data.

        body must either be UTF-8-encoded bytes, a string, or a dict or
        list containing values that can be encoded as JSON.

        The Content-Type header of the request will be set to
        "application/json; charset=utf-8".

        Sending JSON data will not work with GET requests.
        """
        self.content_type = "application/json; charset=utf-8"
        if isinstance(body, str):
            self.body = body.encode("utf-8")
        elif isinstance(body, bytes):
            self.body = body
        elif isinstance(body, (dict, list)):
            self.body = json.dumps(body).encode("ascii")
        else:
            raise TypeError("body must be one of str, bytes, list, or dict")

    def set_env_var(self, name: str, value: Any) -> None:
        self._extra_environ[name] = value

    def set_header(self, name: str, value: str) -> None:
        if name.lower() == "content-type":
            self.content_type = value
        else:
            self._extra_headers.append((name, value))

    def add_argument(self, name: str, value: str | Iterable[str]) -> None:
        """Add a CGI argument to this request.

        For GET and HEAD requests, this will add a query string to the
        URL, for other requests it will include the arguments in the
        request body.
        """
        if self.body != b"":
            raise ValueError(
                "setting arguments and a body is mutually exclusive"
            )
        values = [value] if isinstance(value, str) else list(value)
        for v in values:
            self._arguments.append((name, v))

    def add_file_argument(
        self,
        name: str,
        content: bytes,
        content_type: str,
        *,
        filename: str | None = None,
    ) -> None:
        """Add a file CGI argument to this request.

        This is not available for GET and HEAD requests. In other requests
        it will force a multipart request body.
        """
        if self.method in ["GET", "HEAD"]:
            raise ValueError(
                "file arguments not supported in GET and HEAD requests"
            )
        if self.body != b"":
            raise ValueError(
                "setting arguments and a body is mutually exclusive"
            )
        self._file_arguments.append((name, content, content_type, filename))

    def clear_arguments(self) -> None:
        self._arguments = []

    def to_environment(self) -> WSGIEnvironment:
        env = {
            "REQUEST_METHOD": self.method,
            "PATH_INFO": self.path,
            "SERVER_NAME": "www.example.com",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "REMOTE_ADDR": "127.0.0.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.errors": self.error_stream,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": True,
        }
        for header, value in self._extra_headers:
            env["HTTP_" + header.upper().replace("-", "_")] = value
        body = self._body
        if self._file_arguments:
            assert body == b""
            body = self._build_multipart_body()
        elif self._arguments:
            if self.method == "GET":
                env["QUERY_STRING"] = self._build_query_string()
            else:
                assert body == b""
                body = self._build_query_string().encode("ascii")
        env["wsgi.input"] = BytesIO(body)
        if body != b"":
            env["CONTENT_LENGTH"] = str(len(body))
        content_type = self._determine_content_type()
        if content_type is not None:
            env["CONTENT_TYPE"] = content_type
        env.update(self._extra_environ)
        return env

    def _determine_content_type(self) -> str | None:
        if self.content_type is not None:
            return self.content_type
        elif self._file_arguments:
            boundary = self._ensure_boundary()
            return f"multipart/form-data; boundary={boundary}"
        elif self.method not in ["GET", "HEAD"] and self._arguments:
            return "application/x-www-form-urlencoded"
        else:
            return None

    def _build_query_string(self) -> str:
        parts: list[str] = []
        for name, value in self._arguments:
            parts.append("{}={}".format(quote_plus(name), quote_plus(value)))
        return "&".join(parts)

    def _build_multipart_body(self) -> bytes:
        boundary = self._ensure_boundary()
        body = b""
        for name, value in self._arguments:
            body += b"--" + boundary.encode("ascii") + b"\r\n"
            body += (
                b'Content-Disposition: form-data; name="'
                + quote_plus(name).encode("ascii")
                + b'"\r\n\r\n'
            )
            body += value.encode("utf-8")
            body += b"\r\n"
        for name, content, content_type, filename in self._file_arguments:
            body += b"--" + boundary.encode("ascii") + b"\r\n"
            body += (
                b'Content-Disposition: form-data; name="'
                + quote_plus(name).encode("ascii")
            ) + b'"; '
            if filename:
                body += b"filename*=UTF-8''" + quote_plus(filename).encode(
                    "ascii"
                )
            else:
                body += b'filename=""'
            body += b"\r\n"
            body += b"Content-Type: " + content_type.encode("ascii") + b"\r\n"
            body += (
                b"Content-Length: "
                + str(len(content)).encode("ascii")
                + b"\r\n\r\n"
            )
            body += content + b"\r\n"
        body += b"--" + boundary.encode("ascii") + b"--\r\n"
        return body

    def _ensure_boundary(self) -> str:
        if self._boundary is None:
            self._boundary = secrets.token_hex()
        return self._boundary


def create_request(method: str, path: str) -> TestRequest:
    return TestRequest(method, path)


class TestResponse:
    def __init__(self, status_line: str, headers: list[Header]) -> None:
        m = _STATUS_RE.match(status_line)
        if not m:
            raise ValueError("invalid status line")
        self.status_line = status_line
        self.status = HTTPStatus(int(m.group(1)))
        self._headers = headers
        self.body = b""

    def get_header_value(self, name: str) -> str:
        for n, v in self._headers:
            if n.lower() == name.lower():
                return v
        raise ValueError("header '{}' not in response".format(name))

    def parse_json_body(self) -> Any:
        """Return the response body as a JSON value.

        Raise an AssertionError if the response headers are incorrect or
        the JSON response is invalid.
        """
        self.assert_content_type(
            "application/json", charset=[None, "us-ascii", "utf-8"]
        )
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError) as exc:
            raise AssertionError(str(exc)) from exc

    def assert_status(self, status: HTTPStatus) -> None:
        assert (
            status == self.status
        ), f"unexpected HTTP status: {status.value} != {self.status.value}"

    def assert_header_not_set(self, name: str) -> None:
        for n, v in self._headers:
            if n.lower() == name.lower():
                raise AssertionError(f"header '{name}' unexpectedly set")

    def assert_header_equal(self, name: str, expected_value: str) -> None:
        try:
            real_value = self.get_header_value(name)
        except ValueError:
            raise AssertionError("missing header '{}'".format(name))
        assert real_value == expected_value, (
            f"header value of '{name}' differs: "
            f"{real_value!r} != {expected_value!r}"
        )

    def _assert_location_response(
        self, expected_status: HTTPStatus, expected_location: str
    ) -> None:
        self.assert_status(expected_status)
        if ":" in expected_location:
            self.assert_header_equal("Location", expected_location)
        else:
            real_location = self.get_header_value("Location")
            parsed = urlparse(real_location)
            real_location = parsed.path
            if parsed.query:
                real_location += "?" + parsed.query
            if parsed.fragment:
                real_location += "#" + parsed.fragment
            assert real_location == expected_location, (
                f"unexpected location: {real_location!r} != "
                f"{expected_location!r}"
            )

    def assert_created_at(self, expected_location: str) -> None:
        """Assert a correct 201 Created response.

        The expected location can either be an absolute URL, or just the
        path portion.
        """
        self._assert_location_response(HTTPStatus.CREATED, expected_location)

    def assert_see_other(self, expected_location: str) -> None:
        """Assert a correct 303 See Other response.

        The expected location can either be an absolute URL, or just the
        path portion.
        """
        self._assert_location_response(HTTPStatus.SEE_OTHER, expected_location)

    def assert_temporary_redirect(self, expected_location: str) -> None:
        """Assert a correct 307 Temporary Redirect response.

        The expected location can either be an absolute URL, or just the
        path portion.
        """
        self._assert_location_response(
            HTTPStatus.TEMPORARY_REDIRECT, expected_location
        )

    def assert_content_type(
        self,
        content_type: str,
        *,
        charset: str | Sequence[str | None] | None = None,
    ) -> None:
        """Assert the response's Content-Type header.

        If the optional charset argument is given, compare the charset
        as well. This can be either a string or a sequence of strings. If
        the list includes the value None, the charset is optional.

        """
        try:
            value = self.get_header_value("Content-Type")
        except ValueError:
            raise AssertionError("missing header 'Content-Type'")
        type_, options = parse_options_header(value)
        assert (
            type_ == content_type
        ), f"unexpected content type: {type_!r} != {content_type!r}"
        if charset is not None:
            cs_list = [charset] if isinstance(charset, str) else charset
            try:
                got_charset = options["charset"]
            except KeyError:
                if None in cs_list:
                    return
                raise AssertionError("no charset in Content-Type header")
            assert got_charset in cs_list, (
                f"unexpected content type charset: "
                f"{got_charset!r} not in {cs_list!r}"
            )

    def assert_set_cookie(
        self,
        expected_name: str,
        expected_value: str,
        *,
        secure: bool | None = None,
        http_only: bool | None = None,
        max_age: int | None = None,
    ) -> None:
        def assert_flag(flag: bool | None, name_: str) -> None:
            if flag:
                if find_arg(name_) is None:
                    raise AssertionError(
                        f"Set-Cookie does not contain the '{name_}' flag"
                    )
            elif flag is not None and not flag:
                if find_arg(name_) is not None:
                    raise AssertionError(
                        f"Set-Cookie contains the '{name_}' flag unexpectedly"
                    )

        def find_arg(arg_name: str) -> str | None:
            for a in args:
                if a[0].lower() == arg_name.lower():
                    return a[1] if len(a) >= 2 else ""
            return None

        def expect_arg(arg_name: str) -> str:
            arg_value = find_arg(arg_name)
            if arg_value is None:
                raise AssertionError(
                    "Set-Cookie does not contain the '{}' argument".format(
                        name
                    )
                )
            return arg_value

        try:
            header_value = self.get_header_value("Set-Cookie")
        except ValueError:
            raise AssertionError("missing header 'Set-Cookie'")
        args = [s.strip().split("=", 1) for s in header_value.split(";")]
        if len(args[0]) < 2:
            raise AssertionError("invalid Set-Cookie header")
        name, value = args[0]
        assert (
            name == expected_name
        ), f"wrong cookie name, {name!r} != {expected_name!r}"
        assert (
            value == expected_value
        ), f"wrong cookie value, {value!r} != {expected_value!r}"
        assert_flag(secure, "Secure")
        assert_flag(http_only, "HttpOnly")
        if max_age is not None:
            age = expect_arg("Max-Age")
            try:
                int_age = int(age)
            except ValueError:
                raise AssertionError("Set-Cookie max-age is not numeric")
            assert (
                int_age == max_age
            ), f"wrong max-age: {int_age!r} != {max_age!r}"


def test_wsgi_app(app: WSGIApplication, request: TestRequest) -> TestResponse:
    output_written = False
    response: TestResponse | None = None

    def write(b: bytes) -> None:
        nonlocal output_written
        assert response is not None
        if b:
            response.body += b
            output_written = True

    def start_response(
        status: str,
        response_headers: list[Header],
        exc_info: tuple[type[BaseException], BaseException, TracebackType]
        | None = None,
    ) -> Callable[[bytes], Any]:
        nonlocal response
        if response and not exc_info:
            raise AssertionError("start_response called multiple times")
        if output_written:
            assert exc_info is not None
            raise exc_info[1].with_traceback(exc_info[2])
        response = TestResponse(status, response_headers)
        return write

    env = request.to_environment()
    body = app(env, start_response)
    if response is None:
        raise AssertionError("start_response() was not called")
    for item in body:
        response.body += item
    return response


ArgumentToTest = Union[
    "tuple[str, Multiplicity, str]", "tuple[str, Multiplicity, str, str]"
]


def test_wsgi_arguments(
    app: WSGIApplication,
    request: TestRequest,
    arguments: Iterable[ArgumentToTest],
) -> None:
    def is_required(argument: ArgumentToTest) -> bool:
        return argument[1] in (
            Multiplicity.REQUIRED,
            Multiplicity.REQUIRED_ANY,
        )

    def setup_args(args: Iterable[ArgumentToTest]) -> None:
        request.clear_arguments()
        if not args and request.method != "GET":
            request.content_type = "application/x-www-form-urlencoded"
        for argument in args:
            assert len(argument) == 3 or len(argument) == 4
            name, multi, valid_value = argument[:3]
            request.add_argument(name, valid_value)

    def setup_required_args_except(argument_name: str) -> None:
        setup_args(
            a for a in arguments if is_required(a) and a[0] != argument_name
        )

    def call_expect_success() -> None:
        response = test_wsgi_app(app, request)
        if response.status == HTTPStatus.BAD_REQUEST:
            raise AssertionError(
                "Bad Request returned, although CGI arguments were correct"
            )
        elif response.status.value >= 400:
            raise AssertionError(
                f"status was: {response.status.value}, "
                f"but expected a successful result"
            )

    def call_expect_bad_request(message: str) -> None:
        response = test_wsgi_app(app, request)
        if response.status != HTTPStatus.BAD_REQUEST:
            raise AssertionError(message)

    def assert_success_required_arguments() -> None:
        setup_args(a for a in arguments if is_required(a))
        call_expect_success()

    def assert_success_all_arguments() -> None:
        setup_args(arguments)
        call_expect_success()

    def assert_failure_if_argument_required_but_missing(
        argument: ArgumentToTest,
    ) -> None:
        if not is_required(arg):
            return
        setup_required_args_except(argument[0])
        call_expect_bad_request(
            "Bad Request not returned, although required CGI argument "
            f"'{argument[0]}' was missing"
        )

    def assert_failure_if_argument_invalid(argument: ArgumentToTest) -> None:
        if len(argument) != 4:  # argument has no invalid value
            return
        name, _, __, invalid_value = argument  # type: ignore
        setup_required_args_except(name)
        request.add_argument(name, invalid_value)
        call_expect_bad_request(
            f"Bad Request not returned, although CGI argument '{name}' "
            f"had invalid value '{invalid_value}'"
        )

    assert_success_required_arguments()
    assert_success_all_arguments()
    for arg in arguments:
        assert_failure_if_argument_required_but_missing(arg)
    for arg in arguments:
        assert_failure_if_argument_invalid(arg)


class RouterTestCase(TestCase):
    @before
    def setup_router(self) -> None:
        self.router = self.create_router()
        self.router.error_handling = False

    def create_router(self) -> Router:
        raise NotImplementedError()

    def send_request(self, request: TestRequest) -> TestResponse:
        return test_wsgi_app(self.router, request)

    def assert_arguments(
        self, request: TestRequest, arguments: Iterable[ArgumentToTest]
    ) -> None:
        test_wsgi_arguments(self.router, request, arguments)


# pytest-friendly aliases
FakeRequest = TestRequest
FakeResponse = TestResponse
run_wsgi_test = test_wsgi_app
