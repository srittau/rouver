import sys
from http import HTTPStatus
from io import BytesIO
from typing import Iterable, Optional, Tuple, Any, Sequence

from asserts import \
    assert_equal, assert_is_instance, assert_has_attr, assert_is_none, \
    assert_dict_superset, assert_not_in, assert_raises, assert_succeeds, \
    assert_true, assert_is_not_none, assert_false

from dectest import TestCase, test

from rouver.args import Multiplicity, parse_args, ArgumentTemplate
from rouver.exceptions import ArgumentsError
from rouver.test import create_request, TestResponse, test_wsgi_app, \
    test_wsgi_arguments, ArgumentToTest
from rouver.types import WSGIEnvironment, StartResponse, WSGIApplication


def assert_wsgi_input_stream(stream: object) -> None:
    assert_has_attr(stream, "read")
    assert_has_attr(stream, "readline")
    assert_has_attr(stream, "readlines")
    assert_has_attr(stream, "__iter__")


class TestRequestTest(TestCase):
    @test
    def attributes(self) -> None:
        request = create_request("GET", "/foo/bar")
        assert_equal("GET", request.method)
        assert_equal("/foo/bar", request.path)
        assert_is_none(request.content_type)
        assert_is_instance(request.error_stream, BytesIO)

    @test
    def capitalize_method(self) -> None:
        request = create_request("pOst", "/foo/bar")
        assert_equal("POST", request.method)

    @test
    def to_environment__minimal(self) -> None:
        request = create_request("GET", "/foo/bar")
        environ = request.to_environment()
        assert_dict_superset({
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/foo/bar",
            "SERVER_NAME": "www.example.com",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": True,
            "wsgi.errors": request.error_stream,
        }, environ)
        assert_wsgi_input_stream(environ["wsgi.input"])
        assert_not_in("CONTENT_TYPE", environ)
        assert_not_in("QUERY_STRING", environ)

    @test
    def add_argument__content_type(self) -> None:
        request = create_request("POST", "/foo/bar")
        assert_is_none(request.content_type)

        request.add_argument("foo", "bar")
        assert_equal("application/x-www-form-urlencoded", request.content_type)

        request.content_type = "image/png"
        request.add_argument("abc", "def")
        assert_equal("image/png", request.content_type)

        request = create_request("GET", "/foo/bar")
        assert_is_none(request.content_type)
        request.add_argument("foo", "bar")
        assert_is_none(request.content_type)

    @test
    def to_environment__content_type(self) -> None:
        request = create_request("GET", "/foo/bar")
        request.content_type = "image/png"
        environ = request.to_environment()
        assert_dict_superset({
            "CONTENT_TYPE": "image/png",
        }, environ)

    @test
    def arguments__get_request(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("foo", "bar")
        request.add_argument("abc", ["def", "ghi"])
        environ = request.to_environment()
        assert_dict_superset({
            "QUERY_STRING": "foo=bar&abc=def&abc=ghi",
        }, environ)

    @test
    def arguments__put_request(self) -> None:
        request = create_request("PUT", "/foo")
        request.add_argument("foo", "bar")
        request.add_argument("abc", ["def", "ghi"])
        environ = request.to_environment()
        assert_not_in("QUERY_STRING", environ)
        assert_equal("application/x-www-form-urlencoded",
                     environ["CONTENT_TYPE"])
        content = environ["wsgi.input"].read()
        assert_equal(b"foo=bar&abc=def&abc=ghi", content)

    @test
    def arguments__quote(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("föo", "bär")
        environ = request.to_environment()
        assert_dict_superset({
            "QUERY_STRING": "f%C3%B6o=b%C3%A4r",
        }, environ)

    @test
    def clear_arguments(self) -> None:
        request = create_request("GET", "/foo")
        request.add_argument("foo", "bar")
        request.clear_arguments()
        environ = request.to_environment()
        assert_not_in("QUERY_STRING", environ)

        request = create_request("POST", "/foo")
        request.add_argument("foo", "bar")
        request.clear_arguments()
        environ = request.to_environment()
        content = environ["wsgi.input"].read()
        assert_equal(b"", content)


class TestResponseTest(TestCase):
    @test
    def attributes(self) -> None:
        response = TestResponse("200 OK", [])
        assert_equal("200 OK", response.status_line)
        assert_equal(HTTPStatus.OK, response.status)
        assert_equal(b"", response.body)

    @test
    def unknown_status(self) -> None:
        with assert_raises(ValueError):
            TestResponse("999 Unknown", [])

    @test
    def invalid_status_line(self) -> None:
        with assert_raises(ValueError):
            TestResponse("INVALID", [])

    @test
    def get_header_value(self) -> None:
        response = TestResponse("200 OK", [
            ("X-Header", "Foobar"),
            ("Content-Type", "image/png"),
            ("Allow", "GET"),
        ])
        assert_equal("image/png", response.get_header_value("Content-Type"))
        assert_equal("image/png", response.get_header_value("content-TYPE"))
        with assert_raises(ValueError):
            response.get_header_value("X-Unknown")

    @test
    def assert_status__ok(self) -> None:
        response = TestResponse("404 Not Found", [])
        with assert_succeeds(AssertionError):
            response.assert_status(HTTPStatus.NOT_FOUND)

    @test
    def assert_status__fail(self) -> None:
        response = TestResponse("404 Not Found", [])
        with assert_raises(AssertionError):
            response.assert_status(HTTPStatus.OK)

    @test
    def assert_header_equal__no_such_header(self) -> None:
        response = TestResponse("200 OK", [("X-Other", "value")])
        with assert_raises(AssertionError):
            response.assert_header_equal("X-Header", "value")

    @test
    def assert_header_equal__ok(self) -> None:
        response = TestResponse("200 OK", [("X-Header", "value")])
        with assert_succeeds(AssertionError):
            response.assert_header_equal("X-Header", "value")

    @test
    def assert_header_equal__differs(self) -> None:
        response = TestResponse("200 OK", [("X-Header", "other")])
        with assert_raises(AssertionError):
            response.assert_header_equal("X-Header", "value")

    @test
    def assert_created_at__ok(self) -> None:
        response = TestResponse(
            "201 Created", [("Location", "http://example.com/")])
        with assert_succeeds(AssertionError):
            response.assert_created_at("http://example.com/")

    @test
    def assert_created_at__not_created(self) -> None:
        response = TestResponse(
            "200 OK", [("Location", "http://example.com/")])
        with assert_raises(AssertionError):
            response.assert_created_at("http://example.com/")

    @test
    def assert_created_at__no_location_header(self) -> None:
        response = TestResponse("201 Created", [])
        with assert_raises(AssertionError):
            response.assert_created_at("http://example.org/")

    @test
    def assert_created_at__wrong_location(self) -> None:
        response = TestResponse(
            "201 Created", [("Location", "http://example.com/")])
        with assert_raises(AssertionError):
            response.assert_created_at("http://example.org/")

    @test
    def assert_created_at__relative_location(self) -> None:
        response = TestResponse(
            "201 Created", [("Location", "http://example.com/foo/bar")])
        with assert_succeeds(AssertionError):
            response.assert_created_at("/foo/bar")


class TestWSGIAppTest(TestCase):
    @test
    def run_app(self) -> None:
        app_run = False
        env = None  # type: Optional[WSGIEnvironment]

        def app(environ: WSGIEnvironment, sr: StartResponse) \
                -> Iterable[bytes]:
            nonlocal app_run, env
            app_run = True
            env = environ
            sr("200 OK", [])
            return []

        request = create_request("GET", "/foo/bar")
        request.add_argument("foo", "bar")
        test_wsgi_app(app, request)
        assert_true(app_run, "app not run")
        assert env is not None
        assert_equal("foo=bar", env.get("QUERY_STRING"))

    @test
    def response(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) \
                -> Iterable[bytes]:
            sr("404 Not Found", [("X-Foo", "Bar")])
            return []

        request = create_request("GET", "/foo/bar")
        response = test_wsgi_app(app, request)
        response.assert_status(HTTPStatus.NOT_FOUND)
        response.assert_header_equal("X-Foo", "Bar")

    @test
    def response_body(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) \
                -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"Abc")
            writer(b"def")
            return [b"Foo", b"bar"]

        request = create_request("GET", "/foo/bar")
        response = test_wsgi_app(app, request)
        assert_equal(b"AbcdefFoobar", response.body)

    @test
    def start_response_not_called(self) -> None:
        def app(_: WSGIEnvironment, __: StartResponse) -> Iterable[bytes]:
            return []

        request = create_request("GET", "/foo/bar")
        with assert_raises(AssertionError):
            test_wsgi_app(app, request)

    @test
    def start_response_called_multiple_times(self) -> None:
        assert_raised = False

        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            nonlocal assert_raised
            sr("200 OK", [])
            try:
                sr("404 Not Found", [])
            except AssertionError:
                assert_raised = True
            return []

        request = create_request("GET", "/foo/bar")
        test_wsgi_app(app, request)
        assert_true(assert_raised)

    @test
    def start_response_called_multiple_times_with_exc_info(self) -> None:
        assert_raised = False

        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            nonlocal assert_raised
            sr("200 OK", [])
            try:
                sr("404 Not Found", [], _get_exc_info())
            except AssertionError:
                assert_raised = True
            return []

        request = create_request("GET", "/foo/bar")
        test_wsgi_app(app, request)
        assert_false(assert_raised)

    @test
    def start_response_called_after_output_written(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"abc")
            sr("404 OK", [], _get_exc_info())
            return []

        request = create_request("GET", "/foo/bar")
        with assert_raises(ValueError):
            test_wsgi_app(app, request)

    @test
    def start_response_called_no_output_written(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            writer = sr("200 OK", [])
            writer(b"")
            sr("404 OK", [], _get_exc_info())
            return []

        request = create_request("GET", "/foo/bar")
        response = test_wsgi_app(app, request)
        response.assert_status(HTTPStatus.NOT_FOUND)


def _get_exc_info() -> Tuple[Any, Any, Any]:
    try:
        raise ValueError()
    except:  # noqa
        return sys.exc_info()


class TestWSGIArgumentsTest(TestCase):
    def _create_app(self, argument_template: Sequence[ArgumentTemplate]) \
            -> WSGIApplication:
        def app(env: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            try:
                parse_args(env, argument_template)
            except ArgumentsError:
                sr("400 Bad Request", [])
            else:
                sr("200 OK", [])
            return []
        return app

    def _successful_arg_test(self,
                             app_args: Sequence[ArgumentTemplate],
                             expected_args: Iterable[ArgumentToTest]) -> None:
        app = self._create_app(app_args)
        request = create_request("GET", "/")
        with assert_succeeds(AssertionError):
            test_wsgi_arguments(app, request, expected_args)

    def _failing_arg_test(self,
                          app_args: Sequence[ArgumentTemplate],
                          expected_args: Iterable[ArgumentToTest]) -> None:
        app = self._create_app(app_args)
        request = create_request("GET", "/")
        with assert_raises(AssertionError):
            test_wsgi_arguments(app, request, expected_args)

    @test
    def no_expected_args(self) -> None:
        self._successful_arg_test([], [])

    @test
    def required_argument_present(self) -> None:
        self._successful_arg_test([
            ("arg", int, Multiplicity.REQUIRED),
        ], [
            ("arg", Multiplicity.REQUIRED, "42"),
        ])

    @test
    def required_argument_not_in_app(self) -> None:
        self._failing_arg_test([
            ("arg", int, Multiplicity.OPTIONAL),
        ], [
            ("arg", Multiplicity.REQUIRED, "42"),
        ])

    @test
    def required_argument_not_in_test(self) -> None:
        self._failing_arg_test([
            ("arg", int, Multiplicity.REQUIRED),
        ], [])

    @test
    def required_argument_optional_in_test(self) -> None:
        self._failing_arg_test([
            ("arg", int, Multiplicity.REQUIRED),
        ], [
            ("arg", Multiplicity.OPTIONAL, "42"),
        ])

    @test
    def optional_argument_not_in_app(self) -> None:
        self._successful_arg_test([
        ], [
            ("arg", Multiplicity.OPTIONAL, "foo"),
        ])

    @test
    def optional_argument_not_in_test(self) -> None:
        self._successful_arg_test([
            ("arg", int, Multiplicity.OPTIONAL),
        ], [])

    @test
    def correct_value_not_accepted(self) -> None:
        self._failing_arg_test([
            ("arg", int, Multiplicity.OPTIONAL),
        ], [
            ("arg", Multiplicity.OPTIONAL, "not-a-number"),
        ])

    @test
    def invalid_value_accepted(self) -> None:
        self._failing_arg_test([
            ("arg", str, Multiplicity.OPTIONAL),
        ], [
            ("arg", Multiplicity.OPTIONAL, "42", "not-a-number"),
        ])

    @test
    def handle_other_errors(self) -> None:
        def app(_: WSGIEnvironment, sr: StartResponse) -> Iterable[bytes]:
            sr("500 Internal Server Error", [])
            return []

        request = create_request("POST", "/")
        with assert_raises(AssertionError):
            test_wsgi_arguments(app, request, [])

    @test
    def post_request__no_args(self) -> None:
        app = self._create_app([
            ("arg", int, Multiplicity.OPTIONAL),
        ])
        request = create_request("POST", "/")
        with assert_succeeds(AssertionError):
            test_wsgi_arguments(app, request, [])
