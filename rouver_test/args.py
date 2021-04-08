from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from urllib.parse import quote_plus

from asserts import (
    assert_equal,
    assert_in,
    assert_not_in,
    assert_raises,
    assert_succeeds,
    fail,
)
from dectest import TestCase, before, test
from werkzeug.exceptions import BadRequest

from rouver.args import ArgumentParser, Multiplicity, parse_args
from rouver.exceptions import ArgumentsError
from rouver_test.testutil import default_environment

MULTIPART_PART_TMPL = """--1234567890
Content-Disposition: form-data; name="{name}"

{value}
"""

MULTIPART_FILE_BODY_TMPL = """--1234567890
Content-Disposition: form-data; name="{name}"; filename={filename}
Content-Type: {type}

{content}
--1234567890--
"""


class ParseArgsTest(TestCase):
    @before
    def setup_environment(self) -> None:
        self.env = default_environment()

    def add_path_argument(self, name: str, value: str) -> None:
        if "QUERY_STRING" not in self.env:
            self.env["QUERY_STRING"] = ""
        if self.env["QUERY_STRING"]:
            self.env["QUERY_STRING"] += "&"
        self.env["QUERY_STRING"] += "{}={}".format(
            quote_plus(name), quote_plus(value)
        )

    def setup_empty_urlencoded_request(self) -> None:
        self.env[
            "CONTENT_TYPE"
        ] = "application/x-www-form-urlencoded; charset=utf-8"

    def setup_urlencoded_request(self, name: str, value: str) -> None:
        self.setup_empty_urlencoded_request()
        body = "{}={}".format(name, value).encode("utf-8")
        self.env["CONTENT_LENGTH"] = str(len(body))
        self.env["wsgi.input"] = BytesIO(body)

    def setup_multipart_request(
        self, name: str, value: str | Iterable[str]
    ) -> None:
        self.env["CONTENT_TYPE"] = "multipart/form-data; boundary=1234567890"
        if isinstance(value, str):
            value = [value]
        body = (
            "".join(
                MULTIPART_PART_TMPL.format(name=name, value=v) for v in value
            )
            + "--1234567890--"
        ).encode("utf-8")
        self.env["CONTENT_LENGTH"] = str(len(body))
        self.env["wsgi.input"] = BytesIO(body)

    def setup_multipart_file_request(
        self, name: str, filename: str, file_content: str, content_type: str
    ) -> None:
        self.env["CONTENT_TYPE"] = "multipart/form-data; boundary=1234567890"
        body = MULTIPART_FILE_BODY_TMPL.format(
            name=name,
            filename=filename,
            content=file_content,
            type=content_type,
        ).encode("utf-8")
        self.env["CONTENT_LENGTH"] = str(len(body))
        self.env["wsgi.input"] = BytesIO(body)

    @test
    def parse_nothing(self) -> None:
        args = parse_args(self.env, [])
        assert_equal({}, args)

    @test
    def invalid_value_parser(self) -> None:
        with assert_raises(TypeError):
            parse_args(
                self.env,
                [
                    (
                        "foo",  # type: ignore
                        "INVALID",
                        Multiplicity.OPTIONAL,
                    )
                ],
            )

    @test
    def parse_str_arg(self) -> None:
        self.add_path_argument("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.REQUIRED)])
        assert_equal({"foo": "bar"}, args)

    @test
    def parse_unicode_arg(self) -> None:
        self.add_path_argument("föo", "bär")
        args = parse_args(self.env, [("föo", str, Multiplicity.REQUIRED)])
        assert_equal({"föo": "bär"}, args)

    @test
    def parse_int_arg(self) -> None:
        self.add_path_argument("foo", "123")
        args = parse_args(self.env, [("foo", int, Multiplicity.REQUIRED)])
        assert_equal({"foo": 123}, args)

    @test
    def parse_invalid_int_arg(self) -> None:
        self.add_path_argument("foo", "bar")
        try:
            parse_args(self.env, [("foo", int, Multiplicity.REQUIRED)])
        except ArgumentsError as exc:
            assert_equal(
                {"foo": "invalid literal for int() with base 10: 'bar'"},
                exc.arguments,
            )
        else:
            fail("ArgumentsError not raised")

    @test
    def required_argument_missing(self) -> None:
        try:
            parse_args(self.env, [("foo", str, Multiplicity.REQUIRED)])
        except ArgumentsError as exc:
            assert_equal({"foo": "mandatory argument missing"}, exc.arguments)
        else:
            fail("ArgumentsError not raised")

    @test
    def optional_argument(self) -> None:
        self.add_path_argument("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": "bar"}, args)

    @test
    def optional_argument_missing(self) -> None:
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({}, args)

    @test
    def optional_argument_empty(self) -> None:
        self.add_path_argument("foo", "")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": ""}, args)

    @test
    def any_argument_empty(self) -> None:
        args = parse_args(self.env, [("foo", int, Multiplicity.ANY)])
        assert_equal({"foo": []}, args)

    @test
    def any_argument(self) -> None:
        self.add_path_argument("foo", "123")
        self.add_path_argument("foo", "456")
        self.add_path_argument("foo", "789")
        args = parse_args(self.env, [("foo", int, Multiplicity.ANY)])
        assert_equal({"foo": [123, 456, 789]}, args)

    @test
    def required_any_argument(self) -> None:
        self.add_path_argument("foo", "123")
        self.add_path_argument("foo", "456")
        self.add_path_argument("foo", "789")
        args = parse_args(self.env, [("foo", int, Multiplicity.REQUIRED_ANY)])
        assert_equal({"foo": [123, 456, 789]}, args)

    @test
    def required_any_argument_missing(self) -> None:
        try:
            parse_args(self.env, [("foo", int, Multiplicity.REQUIRED_ANY)])
        except ArgumentsError as exc:
            assert_equal({"foo": "mandatory argument missing"}, exc.arguments)
        else:
            fail("ArgumentsError not raised")

    @test
    def urlencoded_post_request(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": "bar"}, args)

    @test
    def urlencoded_post_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_urlencoded_request("föo", "bär")
        args = parse_args(self.env, [("föo", str, Multiplicity.OPTIONAL)])
        assert_equal({"föo": "bär"}, args)

    @test
    def urlencoded_patch_request(self) -> None:
        self.env["REQUEST_METHOD"] = "PATCH"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": "bar"}, args)

    @test
    def urlencoded_delete_request(self) -> None:
        self.env["REQUEST_METHOD"] = "DELETE"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": "bar"}, args)

    @test
    def empty_delete__optional(self) -> None:
        self.env["REQUEST_METHOD"] = "DELETE"
        self.setup_empty_urlencoded_request()
        args = parse_args(
            self.env,
            [
                ("opt", str, Multiplicity.OPTIONAL),
                ("any", str, Multiplicity.ANY),
            ],
        )
        assert_not_in("opt", args)
        assert_equal([], args["any"])

    @test
    def empty_delete__required_not_supplied(self) -> None:
        self.env["REQUEST_METHOD"] = "DELETE"
        self.setup_empty_urlencoded_request()
        with assert_raises(ArgumentsError):
            parse_args(
                self.env,
                [
                    ("req", str, Multiplicity.REQUIRED),
                    ("once", str, Multiplicity.REQUIRED_ANY),
                ],
            )

    @test
    def urlencoded_put_request(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": "bar"}, args)

    @test
    def urlencoded_put_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_urlencoded_request("föo", "bär")
        args = parse_args(self.env, [("föo", str, Multiplicity.OPTIONAL)])
        assert_equal({"föo": "bär"}, args)

    @test
    def multipart_post_request(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": "bar"}, args)

    @test
    def multipart_post_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request("föo", "bär")
        args = parse_args(self.env, [("föo", str, Multiplicity.OPTIONAL)])
        assert_equal({"föo": "bär"}, args)

    @test
    def multipart_put_request(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request("foo", "bar")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": "bar"}, args)

    @test
    def multipart_put_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request("föo", "bär")
        args = parse_args(self.env, [("föo", str, Multiplicity.OPTIONAL)])
        assert_equal({"föo": "bär"}, args)

    @test
    def multipart_multiple_arguments(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request("foo", ["bar", "baz"])
        args = parse_args(self.env, [("foo", str, Multiplicity.ANY)])
        assert_equal({"foo": ["bar", "baz"]}, args)

    @test
    def multipart__optional_argument_empty(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request("foo", "")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({"foo": ""}, args)

    @test
    def multipart_post_request_with_file(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            "my-file", "my-file.txt", "content", "text/plain; charset=us-ascii"
        )
        args = parse_args(
            self.env, [("my-file", "file", Multiplicity.REQUIRED)]
        )
        assert_in("my-file", args)
        f = args["my-file"]
        assert_equal("my-file.txt", f.filename)
        assert_equal("text/plain", f.content_type)
        assert_equal(b"content", f.read())

    @test
    def multipart_post_request_with_optional_file(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            "my-file", "my-file.txt", "content", "text/plain; charset=us-ascii"
        )
        args = parse_args(
            self.env, [("my-file", "file-or-str", Multiplicity.REQUIRED)]
        )
        assert_in("my-file", args)
        f = args["my-file"]
        assert_equal("my-file.txt", f.filename)
        assert_equal("text/plain", f.content_type)
        assert_equal(b"content", f.read())

    @test
    def multipart_post_request_with_empty_file(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request("my-file", "test")
        args = parse_args(
            self.env, [("my-file", "file-or-str", Multiplicity.REQUIRED)]
        )
        assert_in("my-file", args)
        assert_equal("test", args["my-file"])

    @test
    def multipart_post_request_with_file_and_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            "föo", "my-filé.txt", "cöntent", "text/plain; charset=utf-8"
        )
        args = parse_args(self.env, [("föo", "file", Multiplicity.REQUIRED)])
        assert_in("föo", args)
        f = args["föo"]
        assert_equal("my-filé.txt", f.filename)
        assert_equal("text/plain", f.content_type)
        assert_equal("cöntent".encode("utf-8"), f.read())

    @test
    def multipart_put_request_with_file(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_file_request(
            "my-file", "my-file.txt", "content", "text/plain"
        )
        args = parse_args(
            self.env, [("my-file", "file", Multiplicity.REQUIRED)]
        )
        assert_in("my-file", args)
        f = args["my-file"]
        assert_equal("my-file.txt", f.filename)
        assert_equal("text/plain", f.content_type)
        assert_equal(b"content", f.read())

    @test
    def read_file_as_value(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            "foo", "my-file.txt", "123", "text/plain"
        )
        args = parse_args(self.env, [("foo", int, Multiplicity.REQUIRED)])
        assert_equal(123, args["foo"])

    @test
    def read_value_as_file(self) -> None:
        self.env["REQUEST_METHOD"] = "GET"
        self.add_path_argument("foo", "bar")
        args = parse_args(self.env, [("foo", "file", Multiplicity.REQUIRED)])
        assert_in("foo", args)
        f = args["foo"]
        assert_equal("", f.filename)
        assert_equal("application/octet-stream", f.content_type)
        assert_equal(b"bar", f.read())

    @test
    def read_value_as_file_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "GET"
        self.add_path_argument("foo", "bär")
        args = parse_args(self.env, [("foo", "file", Multiplicity.REQUIRED)])
        assert_in("foo", args)
        f = args["foo"]
        assert_equal("", f.filename)
        assert_equal("application/octet-stream", f.content_type)
        assert_equal("bär".encode("utf-8"), f.read())

    @test
    def post_wrong_content_type__optional_args(self) -> None:
        """This exposes a bug in Python's cgi module that will raise a
        TypeError when no request string was provided. See
        <https://bugs.python.org/issue32029>.
        """
        self.env["REQUEST_METHOD"] = "POST"
        self.env["CONTENT_TYPE"] = "application/octet-stream"
        self.env["CONTENT_LENGTH"] = "2"
        self.env["wsgi.input"] = BytesIO(b"AB")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({}, args)

    @test
    def post_wrong_content_type__required_args(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.env["CONTENT_TYPE"] = "application/octet-stream"
        self.env["CONTENT_LENGTH"] = "2"
        self.env["wsgi.input"] = BytesIO(b"AB")
        with assert_raises(BadRequest):
            parse_args(self.env, [("foo", str, Multiplicity.REQUIRED)])

    @test
    def patch_wrong_content_type__optional_args(self) -> None:
        self.env["REQUEST_METHOD"] = "PATCH"
        self.env["CONTENT_TYPE"] = "application/octet-stream"
        self.env["CONTENT_LENGTH"] = "2"
        self.env["wsgi.input"] = BytesIO(b"AB")
        args = parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])
        assert_equal({}, args)

    @test
    def patch_wrong_content_type__required_args(self) -> None:
        self.env["REQUEST_METHOD"] = "PATCH"
        self.env["CONTENT_TYPE"] = "application/octet-stream"
        self.env["CONTENT_LENGTH"] = "2"
        self.env["wsgi.input"] = BytesIO(b"AB")
        with assert_raises(BadRequest):
            parse_args(self.env, [("foo", str, Multiplicity.REQUIRED)])

    @test
    def no_exhaustive_check(self) -> None:
        self.add_path_argument("foo", "v")
        self.add_path_argument("unknown", "v")
        with assert_succeeds(ArgumentsError):
            parse_args(self.env, [("foo", str, Multiplicity.OPTIONAL)])

    @test
    def exhaustive_check__succeeds(self) -> None:
        self.add_path_argument("foo", "v")
        with assert_succeeds(ArgumentsError):
            parse_args(
                self.env,
                [("foo", str, Multiplicity.OPTIONAL)],
                exhaustive=True,
            )

    @test
    def exhaustive_check__fails(self) -> None:
        self.add_path_argument("foo", "v")
        self.add_path_argument("unknown", "v")
        try:
            parse_args(
                self.env,
                [("foo", str, Multiplicity.OPTIONAL)],
                exhaustive=True,
            )
        except ArgumentsError as exc:
            assert_equal({"unknown": "unknown argument"}, exc.arguments)
        else:
            fail("ArgumentsError not raised")

    @test
    def unsupported_method(self) -> None:
        self.env["REQUEST_METHOD"] = "UNKNOWN"
        with assert_raises(ValueError):
            parse_args(self.env, [])


class ArgumentParserTest(TestCase):
    @test
    def parse_args__post_twice(self) -> None:
        environ = {
            "wsgi.input": BytesIO(b"foo=bar&abc=def"),
            "REQUEST_METHOD": "POST",
            "CONTENT_LENGTH": "15",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
        }
        parser = ArgumentParser(environ)
        args1 = parser.parse_args([("foo", str, Multiplicity.REQUIRED)])
        assert_equal({"foo": "bar"}, args1)
        args2 = parser.parse_args(
            [
                ("foo", str, Multiplicity.REQUIRED),
                ("abc", str, Multiplicity.REQUIRED),
            ]
        )
        assert_equal({"foo": "bar", "abc": "def"}, args2)

    @test
    def exhaustive_with_previous_calls(self) -> None:
        environ = {
            "wsgi.input": BytesIO(b"foo=bar&abc=def"),
            "REQUEST_METHOD": "POST",
            "CONTENT_LENGTH": "15",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
        }
        parser = ArgumentParser(environ)
        parser.parse_args(
            [("foo", str, Multiplicity.REQUIRED)], exhaustive=False
        )
        with assert_succeeds(ArgumentsError):
            parser.parse_args(
                [("abc", str, Multiplicity.REQUIRED)], exhaustive=True
            )
