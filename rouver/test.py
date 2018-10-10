import json
import re
from http import HTTPStatus
from io import BytesIO
from json import JSONDecodeError
from types import TracebackType
from typing import \
    Optional, Union, Sequence, List, Tuple, Callable, Any, Type, Iterable
from urllib.parse import quote_plus, urlparse

from asserts import fail, assert_equal, assert_in

from dectest import TestCase, before
from werkzeug.http import parse_options_header

from rouver.args import Multiplicity
from rouver.router import Router
from rouver.types import WSGIApplication, WSGIEnvironment, Header

_STATUS_RE = re.compile(r"^(\d\d\d) [ -~]+$")

_exc_info = Tuple[Type[BaseException], BaseException, TracebackType]


class TestRequest:
    def __init__(self, method: str, path: str) -> None:
        self.method = method.upper()
        self.path = path
        self._body = b""
        self.error_stream = BytesIO()
        self.content_type = None  # type: Optional[str]
        self._extra_environ = {}  # type: WSGIEnvironment
        self._extra_headers = []  # type: List[Tuple[str, str]]
        self._arguments = []  # type: List[Tuple[str, str]]

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
                "setting arguments and a body is mutually exclusive")
        self._body = body

    def set_json_request(self, body: Union[str, bytes, dict, list]) -> None:
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

    def prepare_for_arguments(self) -> None:
        if self.body != b"":
            raise ValueError(
                "setting arguments and a body is mutually exclusive")
        if self.method != "GET" and self.content_type is None:
            self.content_type = "application/x-www-form-urlencoded"

    def add_argument(self, name: str, value: Union[str, Sequence[str]]) \
            -> None:
        self.prepare_for_arguments()
        values = [value] if isinstance(value, str) else list(value)
        for v in values:
            self._arguments.append((name, v))

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
            "wsgi.input": BytesIO(self._body),
            "wsgi.errors": self.error_stream,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": True,
        }
        for header, value in self._extra_headers:
            env["HTTP_" + header.upper().replace("-", "_")] = value
        if self._arguments:
            if self.method == "GET":
                env["QUERY_STRING"] = self._build_query_string()
            else:
                assert self._body == b""
                env["wsgi.input"] = \
                    BytesIO(self._build_query_string().encode("ascii"))
        if self._body != b"":
            env["CONTENT_LENGTH"] = str(len(self._body))
        if self.content_type is not None:
            env["CONTENT_TYPE"] = self.content_type
        env.update(self._extra_environ)
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
        self.assert_content_type("application/json",
                                 charset=[None, "us-ascii", "utf-8"])
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError) as exc:
            raise AssertionError(str(exc)) from exc

    def assert_status(self, status: HTTPStatus) -> None:
        assert_equal(status, self.status,
                     msg_fmt="unexpected HTTP status: {msg}")

    def assert_header_not_set(self, name: str) -> None:
        for n, v in self._headers:
            if n.lower() == name.lower():
                fail("header '{}' unexpectedly set".format(name))

    def assert_header_equal(self, name: str, expected_value: str) -> None:
        try:
            real_value = self.get_header_value(name)
        except ValueError:
            raise AssertionError("missing header '{}'".format(name))
        msg = "header value of {} differs: {{msg}}".format(name)
        assert_equal(expected_value, real_value, msg_fmt=msg)

    def _assert_location_response(self, expected_status: HTTPStatus,
                                  expected_location: str) -> None:
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
            assert_equal(expected_location, real_location)

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
        self._assert_location_response(HTTPStatus.TEMPORARY_REDIRECT,
                                       expected_location)

    def assert_content_type(
            self, content_type: str, *,
            charset: Optional[Union[str, Sequence[Optional[str]]]] = None) \
            -> None:
        """Assert the response's Content-Type header.

        If the optional charset argument is given, compare the charset
        as well. This can be either a string or a sequence of strings. If
        the list includes the value None, the charset is optional.

        """
        try:
            value = self.get_header_value("Content-Type")
        except ValueError:
            fail("missing header 'Content-Type'")
        type_, options = parse_options_header(value)
        assert_equal(content_type, type_, "unexpected content type: {msg}")
        if charset is not None:
            cs_list = [charset] if isinstance(charset, str) else charset
            try:
                got_charset = options["charset"]
            except KeyError:
                if None in cs_list:
                    return
                fail("no charset in Content-Type header")
            msg = "unexpected content type charset: {msg}"
            assert_in(got_charset, cs_list, msg)

    def assert_set_cookie(self,
                          expected_name: str,
                          expected_value: str,
                          *,
                          secure: Optional[bool] = None,
                          http_only: Optional[bool] = None,
                          max_age: Optional[int] = None) -> None:
        def assert_flag(flag: Optional[bool], name_: str) -> None:
            if flag:
                if find_arg(name_) is None:
                    fail("Set-Cookie does not contain the {} "
                         "flag".format(name_))
            elif flag is not None and not flag:
                if find_arg(name_) is not None:
                    fail("Set-Cookie contains the {} flag "
                         "unexpectedly".format(name_))

        def find_arg(arg_name: str) -> Optional[str]:
            for a in args:
                if a[0].lower() == arg_name.lower():
                    return a[1] if len(a) >= 2 else ""
            return None

        def expect_arg(arg_name: str) -> str:
            arg_value = find_arg(arg_name)
            if arg_value is None:
                raise AssertionError(
                    "Set-Cookie does not contain the '{}' argument".format(
                        name))
            return arg_value

        try:
            header_value = self.get_header_value("Set-Cookie")
        except ValueError:
            fail("missing header 'Set-Cookie'")
        args = [s.strip().split("=", 1) for s in header_value.split(";")]
        if len(args[0]) < 2:
            raise AssertionError("invalid Set-Cookie header")
        name, value = args[0]
        assert_equal(expected_name, name, "wrong cookie name, {msg}")
        assert_equal(expected_value, value, "wrong cookie value, {msg}")
        assert_flag(secure, "Secure")
        assert_flag(http_only, "HttpOnly")
        if max_age is not None:
            age = expect_arg("Max-Age")
            try:
                int_age = int(age)
            except ValueError:
                fail("Set-Cookie max-age is not numeric")
            assert_equal(max_age, int_age)


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
