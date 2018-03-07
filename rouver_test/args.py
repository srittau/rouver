from unittest import TestCase
from urllib.parse import quote_plus

from asserts import assert_equal, fail, assert_raises, assert_in, assert_not_in
from io import BytesIO

from werkzeug.exceptions import BadRequest

from rouver.args import parse_args, Multiplicity, ArgumentParser
from rouver.exceptions import ArgumentsError

from rouver_test.util import default_environment

MULTIPART_BODY_TMPL = """--1234567890
Content-Disposition: form-data; name="{}"

{}
--1234567890--
"""

MULTIPART_FILE_BODY_TMPL = """--1234567890
Content-Disposition: form-data; name="{name}"; filename={filename}
Content-Type: {type}

{content}
--1234567890--
"""


class ParseArgsTest(TestCase):
    def setUp(self) -> None:
        self.env = default_environment()

    def add_path_argument(self, name: str, value: str) -> None:
        if "QUERY_STRING" not in self.env:
            self.env["QUERY_STRING"] = ""
        if self.env["QUERY_STRING"]:
            self.env["QUERY_STRING"] += "&"
        self.env["QUERY_STRING"] += \
            "{}={}".format(quote_plus(name), quote_plus(value))

    def setup_urlencoded_request(self, name: str, value: str) -> None:
        body = "{}={}".format(name, value).encode("utf-8")
        self.env["CONTENT_TYPE"] = \
            "application/x-www-form-urlencoded; charset=utf-8"
        self.env["CONTENT_LENGTH"] = str(len(body))
        self.env["wsgi.input"] = BytesIO(body)

    def setup_multipart_request(self, name: str, value: str) -> None:
        self.env["CONTENT_TYPE"] = \
            "multipart/form-data; boundary=1234567890"
        body = MULTIPART_BODY_TMPL.format(name, value).encode("utf-8")
        self.env["CONTENT_LENGTH"] = str(len(body))
        self.env["wsgi.input"] = BytesIO(body)

    def setup_multipart_file_request(self, name: str, filename: str,
                                     file_content: str,
                                     content_type: str) -> None:
        self.env["CONTENT_TYPE"] = \
            "multipart/form-data; boundary=1234567890"
        body = MULTIPART_FILE_BODY_TMPL.format(
            name=name,
            filename=filename,
            content=file_content,
            type=content_type).encode("utf-8")
        self.env["CONTENT_LENGTH"] = str(len(body))
        self.env["wsgi.input"] = BytesIO(body)

    def test_parse_nothing(self) -> None:
        args = parse_args(self.env, [])
        assert_equal({}, args)

    def test_invalid_value_parser(self) -> None:
        with assert_raises(TypeError):
            parse_args(self.env, [
                ("foo", "INVALID", Multiplicity.OPTIONAL),
            ])

    def test_parse_str_arg(self) -> None:
        self.add_path_argument("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.REQUIRED),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_parse_unicode_arg(self) -> None:
        self.add_path_argument("föo", "bär")
        args = parse_args(self.env, [
            ("föo", str, Multiplicity.REQUIRED),
        ])
        assert_equal({"föo": "bär"}, args)

    def test_parse_int_arg(self) -> None:
        self.add_path_argument("foo", "123")
        args = parse_args(self.env, [
            ("foo", int, Multiplicity.REQUIRED),
        ])
        assert_equal({"foo": 123}, args)

    def test_parse_invalid_int_arg(self) -> None:
        self.add_path_argument("foo", "bar")
        try:
            parse_args(self.env, [
                ("foo", int, Multiplicity.REQUIRED),
            ])
        except ArgumentsError as exc:
            assert_equal({
                "foo": "invalid literal for int() with base 10: 'bar'",
            }, exc.arguments)
        else:
            fail("ArgumentsError not raised")

    def test_required_argument_missing(self) -> None:
        try:
            parse_args(self.env, [
                ("foo", str, Multiplicity.REQUIRED),
            ])
        except ArgumentsError as exc:
            assert_equal({"foo": "mandatory argument missing"}, exc.arguments)
        else:
            fail("ArgumentsError not raised")

    def test_optional_argument(self) -> None:
        self.add_path_argument("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_optional_argument_missing(self) -> None:
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({}, args)

    def test_any_argument_empty(self) -> None:
        args = parse_args(self.env, [
            ("foo", int, Multiplicity.ANY),
        ])
        assert_equal({"foo": []}, args)

    def test_any_argument(self) -> None:
        self.add_path_argument("foo", "123")
        self.add_path_argument("foo", "456")
        self.add_path_argument("foo", "789")
        args = parse_args(self.env, [
            ("foo", int, Multiplicity.ANY),
        ])
        assert_equal({"foo": [123, 456, 789]}, args)

    def test_required_any_argument(self) -> None:
        self.add_path_argument("foo", "123")
        self.add_path_argument("foo", "456")
        self.add_path_argument("foo", "789")
        args = parse_args(self.env, [
            ("foo", int, Multiplicity.REQUIRED_ANY),
        ])
        assert_equal({"foo": [123, 456, 789]}, args)

    def test_required_any_argument_missing(self) -> None:
        try:
            parse_args(self.env, [
                ("foo", int, Multiplicity.REQUIRED_ANY),
            ])
        except ArgumentsError as exc:
            assert_equal({"foo": "mandatory argument missing"}, exc.arguments)
        else:
            fail("ArgumentsError not raised")

    def test_urlencoded_post_request(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_urlencoded_post_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_urlencoded_request("föo", "bär")
        args = parse_args(self.env, [
            ("föo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"föo": "bär"}, args)

    def test_urlencoded_patch_request(self) -> None:
        self.env["REQUEST_METHOD"] = "PATCH"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_urlencoded_delete_request(self) -> None:
        self.env["REQUEST_METHOD"] = "DELETE"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_empty_delete__optional(self) -> None:
        self.env["REQUEST_METHOD"] = "DELETE"
        args = parse_args(self.env, [
            ("opt", str, Multiplicity.OPTIONAL),
            ("any", str, Multiplicity.ANY),
        ])
        assert_not_in("opt", args)
        assert_equal([], args["any"])

    def test_empty_delete__required_not_supplied(self) -> None:
        self.env["REQUEST_METHOD"] = "DELETE"
        with assert_raises(ArgumentsError):
            parse_args(self.env, [
                ("req", str, Multiplicity.REQUIRED),
                ("once", str, Multiplicity.REQUIRED_ANY),
            ])

    def test_urlencoded_put_request(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_urlencoded_request("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_urlencoded_put_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_urlencoded_request("föo", "bär")
        args = parse_args(self.env, [
            ("föo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"föo": "bär"}, args)

    def test_multipart_post_request(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_multipart_post_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request("föo", "bär")
        args = parse_args(self.env, [
            ("föo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"föo": "bär"}, args)

    def test_multipart_put_request(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request("foo", "bar")
        args = parse_args(self.env, [
            ("foo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"foo": "bar"}, args)

    def test_multipart_put_request_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request("föo", "bär")
        args = parse_args(self.env, [
            ("föo", str, Multiplicity.OPTIONAL),
        ])
        assert_equal({"föo": "bär"}, args)

    def test_multipart_post_request_with_file(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request("my-file", "my-file.txt", "content",
                                          "text/plain")
        args = parse_args(self.env, [
            ("my-file", "file", Multiplicity.REQUIRED),
        ])
        assert_in("my-file", args)
        f = args["my-file"]
        assert_equal("my-file.txt", f.filename)
        assert_equal("text/plain", f.content_type)
        assert_equal(b"content", f.read())

    def test_multipart_post_request_with_file_and_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request("föo", "my-filé.txt", "cöntent",
                                          "text/plain; charset=utf-8")
        args = parse_args(self.env, [
            ("föo", "file", Multiplicity.REQUIRED),
        ])
        assert_in("föo", args)
        f = args["föo"]
        assert_equal("my-filé.txt", f.filename)
        assert_equal("text/plain", f.content_type)
        assert_equal("cöntent".encode("utf-8"), f.read())

    def test_multipart_put_request_with_file(self) -> None:
        self.env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_file_request("my-file", "my-file.txt", "content",
                                          "text/plain")
        args = parse_args(self.env, [
            ("my-file", "file", Multiplicity.REQUIRED),
        ])
        assert_in("my-file", args)
        f = args["my-file"]
        assert_equal("my-file.txt", f.filename)
        assert_equal("text/plain", f.content_type)
        assert_equal(b"content", f.read())

    def test_read_file_as_value(self) -> None:
        self.env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request("foo", "my-file.txt", "123",
                                          "text/plain")
        args = parse_args(self.env, [
            ("foo", int, Multiplicity.REQUIRED),
        ])
        assert_equal(123, args["foo"])

    def test_read_value_as_file(self) -> None:
        self.env["REQUEST_METHOD"] = "GET"
        self.add_path_argument("foo", "bar")
        args = parse_args(self.env, [
            ("foo", "file", Multiplicity.REQUIRED),
        ])
        assert_in("foo", args)
        f = args["foo"]
        assert_equal("", f.filename)
        assert_equal("application/octet-stream", f.content_type)
        assert_equal(b"bar", f.read())

    def test_read_value_as_file_with_umlauts(self) -> None:
        self.env["REQUEST_METHOD"] = "GET"
        self.add_path_argument("foo", "bär")
        args = parse_args(self.env, [
            ("foo", "file", Multiplicity.REQUIRED),
        ])
        assert_in("foo", args)
        f = args["foo"]
        assert_equal("", f.filename)
        assert_equal("application/octet-stream", f.content_type)
        assert_equal("bär".encode("utf-8"), f.read())

    def test_post_wrong_content_type(self) -> None:
        """This exposes a bug in Python's cgi module that will raise a
        TypeError when no request string was provided. See
        <https://bugs.python.org/issue32029>.
        """
        self.env["REQUEST_METHOD"] = "POST"
        self.env["CONTENT_TYPE"] = "application/octet-stream"
        self.env["CONTENT_LENGTH"] = "2"
        self.env["wsgi.input"] = BytesIO(b"AB")
        with assert_raises(BadRequest):
            parse_args(self.env, [
                ("foo", str, Multiplicity.OPTIONAL),
            ])

    def test_patch_wrong_content_type(self) -> None:
        self.env["REQUEST_METHOD"] = "PATCH"
        self.env["CONTENT_TYPE"] = "application/octet-stream"
        self.env["CONTENT_LENGTH"] = "2"
        self.env["wsgi.input"] = BytesIO(b"AB")
        with assert_raises(BadRequest):
            parse_args(self.env, [
                ("foo", str, Multiplicity.OPTIONAL),
            ])


class ArgumentParserTest(TestCase):
    def test_parse_args__post_twice(self) -> None:
        environ = {
            "wsgi.input": BytesIO(b"foo=bar&abc=def"),
            "REQUEST_METHOD": "POST",
            "CONTENT_LENGTH": "15",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
        }
        parser = ArgumentParser(environ)
        args1 = parser.parse_args([
            ("foo", str, Multiplicity.REQUIRED),
        ])
        assert_equal({"foo": "bar"}, args1)
        args2 = parser.parse_args([
            ("foo", str, Multiplicity.REQUIRED),
            ("abc", str, Multiplicity.REQUIRED),
        ])
        assert_equal({"foo": "bar", "abc": "def"}, args2)
