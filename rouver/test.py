import re
from http import HTTPStatus
from io import BytesIO
from types import TracebackType
from typing import \
    Optional, Union, Sequence, List, Tuple, Callable, Any, Type, Iterable
from urllib.parse import quote_plus, urlparse

from asserts import fail, assert_equal

from dectest import TestCase, before

from rouver.args import Multiplicity
from rouver.router import Router
from rouver.types import WSGIApplication, WSGIEnvironment, Header

_STATUS_RE = re.compile(r"^(\d\d\d) [ -~]+$")

_exc_info = Tuple[Type[BaseException], BaseException, TracebackType]


class TestRequest:
    def __init__(self, method: str, path: str) -> None:
        self.method = method.upper()
        self.path = path
        self.error_stream = BytesIO()
        self.content_type = None  # type: Optional[str]
        self._arguments = []  # type: List[Tuple[str, str]]

    def add_argument(self, name: str, value: Union[str, Sequence[str]]) \
            -> None:
        values = [value] if isinstance(value, str) else list(value)
        for v in values:
            self._arguments.append((name, v))
        if self.method != "GET" and self.content_type is None:
            self.content_type = "application/x-www-form-urlencoded"

    def clear_arguments(self) -> None:
        self._arguments = []

    def to_environment(self) -> WSGIEnvironment:
        env = {
            "REQUEST_METHOD": self.method,
            "PATH_INFO": self.path,
            "SERVER_NAME": "www.example.com",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": BytesIO(b""),
            "wsgi.errors": self.error_stream,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": True,
        }
        if self._arguments:
            if self.method == "GET":
                env["QUERY_STRING"] = self._build_query_string()
            else:
                env["wsgi.input"] = \
                    BytesIO(self._build_query_string().encode("ascii"))
        if self.content_type is not None:
            env["CONTENT_TYPE"] = self.content_type
        return env

    def _build_query_string(self) -> str:
        parts = []  # type: List[str]
        for name, value in self._arguments:
            parts.append("{}={}".format(quote_plus(name), quote_plus(value)))
        return "&".join(parts)


def create_request(method: str, path: str) -> TestRequest:
    return TestRequest(method, path)


class TestResponse:
    def __init__(self, status_line: str, headers: List[Header]) -> None:
        pass
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

    def assert_status(self, status: HTTPStatus) -> None:
        assert_equal(status, self.status,
                     msg_fmt="unexpected HTTP status: {msg}")

    def assert_header_equal(self, name: str, expected_value: str) -> None:
        try:
            real_value = self.get_header_value(name)
        except ValueError:
            raise AssertionError("missing header '{}'".format(name))
        msg = "header value of {} differs: {{msg}}".format(name)
        assert_equal(expected_value, real_value, msg_fmt=msg)

    def assert_created_at(self, expected_location: str) -> None:
        self.assert_status(HTTPStatus.CREATED)
        if ":" in expected_location:
            self.assert_header_equal("Location", expected_location)
        else:
            real_location = self.get_header_value("Location")
            parsed = urlparse(real_location)
            assert_equal(expected_location, parsed.path)


def test_wsgi_app(app: WSGIApplication, request: TestRequest) -> TestResponse:
    def write(b: bytes) -> None:
        nonlocal output_written
        assert response is not None
        if b:
            response.body += b
            output_written = True

    def start_response(
            status: str,
            response_headers: List[Header],
            exc_info: Optional[_exc_info] = None
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
    response = None  # type: Optional[TestResponse]
    output_written = False
    body = app(env, start_response)
    if response is None:
        raise AssertionError("start_response() was not called")
    for item in body:
        response.body += item
    return response


ArgumentToTest = Union[
    Tuple[str, Multiplicity, str],
    Tuple[str, Multiplicity, str, str],
]


def test_wsgi_arguments(app: WSGIApplication, request: TestRequest,
                        arguments: Iterable[ArgumentToTest]) -> None:
    def setup_args(args: Iterable[ArgumentToTest]) -> None:
        request.clear_arguments()
        if not args and request.method != "GET":
            request.content_type = "application/x-www-form-urlencoded"
        for argument in args:
            assert len(argument) == 3 or len(argument) == 4
            name, multi, valid_value = argument[:3]
            if multi not in [Multiplicity.REQUIRED, Multiplicity.OPTIONAL]:
                message = "unsupported multiplicity '{}' " \
                          "for argument '{}'".format(multi, name)
                raise ValueError(message)
            request.add_argument(name, valid_value)

    def call_expect_success() -> None:
        response = test_wsgi_app(app, request)
        if response.status == HTTPStatus.BAD_REQUEST:
            fail("Bad Request returned, although CGI arguments were correct")
        elif response.status.value >= 400:
            fail("status was: '{}', but expected a successful result".format(
                response.status))

    def call_expect_bad_request(message: str) -> None:
        response = test_wsgi_app(app, request)
        if response.status != HTTPStatus.BAD_REQUEST:
            fail(message)

    def assert_success_if_mandatory_arguments_ok() -> None:
        setup_args(required_arguments)
        call_expect_success()

    def assert_success_if_all_arguments_ok() -> None:
        setup_args(arguments)
        call_expect_success()

    def assert_failure_if_required_argument_missing(missing_argument: str) \
            -> None:
        setup_args([a for a in required_arguments if a[0] != missing_argument])
        call_expect_bad_request(
            "Bad Request not returned, although required CGI argument "
            "'{}' was missing".format(missing_argument))

    def assert_failure_if_argument_invalid(argument: ArgumentToTest) -> None:
        assert len(argument) >= 4
        name, _, __, invalid_value = argument  # type: ignore
        setup_args([a for a in required_arguments if a[0] != name])
        request.add_argument(name, invalid_value)
        call_expect_bad_request(
            "Bad Request not returned, although CGI argument '" + name +
            "' had invalid value '" + str(invalid_value) + "'")

    required_arguments = \
        [a for a in arguments if a[1] == Multiplicity.REQUIRED]
    wrong_value_arguments = [a for a in arguments if len(a) > 3]

    assert_success_if_mandatory_arguments_ok()
    assert_success_if_all_arguments_ok()
    for arg in required_arguments:
        assert_failure_if_required_argument_missing(arg[0])
    for arg in wrong_value_arguments:
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

    def assert_arguments(self, request: TestRequest,
                         arguments: Iterable[ArgumentToTest]) -> None:
        test_wsgi_arguments(self.router, request, arguments)
