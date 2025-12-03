from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from urllib.parse import quote_plus

import pytest
from werkzeug.exceptions import BadRequest

from rouver.args import ArgumentParser, Multiplicity, parse_args
from rouver.exceptions import ArgumentsError
from rouver.types import WSGIEnvironment
from rouver.util import rfc5987_encode
from rouver_test.testutil import default_environment

MULTIPART_PART_TMPL = """--1234567890
Content-Disposition: form-data; name="{name}"

{value}
"""

MULTIPART_FILE_BODY_TMPL = """--1234567890
Content-Disposition: form-data; name="{name}"; {filename_param}
Content-Type: {type}

{content}
--1234567890--
"""


class TestParseArgs:
    def add_path_argument(
        self, env: WSGIEnvironment, name: str, value: str
    ) -> None:
        if "QUERY_STRING" not in env:
            env["QUERY_STRING"] = ""
        if env["QUERY_STRING"]:
            env["QUERY_STRING"] += "&"
        env["QUERY_STRING"] += "{}={}".format(
            quote_plus(name), quote_plus(value)
        )

    def setup_empty_urlencoded_request(self, env: WSGIEnvironment) -> None:
        env["CONTENT_TYPE"] = (
            "application/x-www-form-urlencoded; charset=utf-8"
        )

    def setup_urlencoded_request(
        self, env: WSGIEnvironment, name: str, value: str
    ) -> None:
        self.setup_empty_urlencoded_request(env)
        body = "{}={}".format(name, value).encode("utf-8")
        env["CONTENT_LENGTH"] = str(len(body))
        env["wsgi.input"] = BytesIO(body)

    def setup_multipart_request(
        self, env: WSGIEnvironment, name: str, value: str | Iterable[str]
    ) -> None:
        env["CONTENT_TYPE"] = "multipart/form-data; boundary=1234567890"
        if isinstance(value, str):
            value = [value]
        body = (
            "".join(
                MULTIPART_PART_TMPL.format(name=name, value=v) for v in value
            )
            + "--1234567890--"
        ).encode("utf-8")
        env["CONTENT_LENGTH"] = str(len(body))
        env["wsgi.input"] = BytesIO(body)

    def setup_multipart_file_request(
        self,
        env: WSGIEnvironment,
        name: str,
        filename: str,
        file_content: str,
        content_type: str,
    ) -> None:
        env["CONTENT_TYPE"] = "multipart/form-data; boundary=1234567890"
        filename_param = rfc5987_encode("filename", filename)
        body = MULTIPART_FILE_BODY_TMPL.format(
            name=name,
            filename_param=filename_param,
            content=file_content,
            type=content_type,
        ).encode("utf-8")
        env["CONTENT_LENGTH"] = str(len(body))
        env["wsgi.input"] = BytesIO(body)

    def test_parse_nothing(self) -> None:
        env = default_environment()
        args = parse_args(env, [])
        assert args == {}

    def test_invalid_value_parser(self) -> None:
        env = default_environment()
        with pytest.raises(TypeError):
            parse_args(
                env,
                [
                    (
                        "foo",  # type: ignore
                        "INVALID",
                        Multiplicity.OPTIONAL,
                    )
                ],
            )

    def test_parse_str_arg(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.REQUIRED)])
        assert args == {"foo": "bar"}

    def test_parse_unicode_arg(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "föo", "bär")
        args = parse_args(env, [("föo", str, Multiplicity.REQUIRED)])
        assert args == {"föo": "bär"}

    def test_parse_int_arg(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "123")
        args = parse_args(env, [("foo", int, Multiplicity.REQUIRED)])
        assert args == {"foo": 123}

    def test_parse_invalid_int_arg(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "bar")
        try:
            parse_args(env, [("foo", int, Multiplicity.REQUIRED)])
        except ArgumentsError as exc:
            assert exc.arguments == {
                "foo": "invalid literal for int() with base 10: 'bar'"
            }
        else:
            pytest.fail("ArgumentsError not raised")

    def test_required_argument_missing(self) -> None:
        env = default_environment()
        try:
            parse_args(env, [("foo", str, Multiplicity.REQUIRED)])
        except ArgumentsError as exc:
            assert exc.arguments == {"foo": "mandatory argument missing"}
        else:
            pytest.fail("ArgumentsError not raised")

    def test_optional_argument(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": "bar"}

    def test_optional_argument_missing(self) -> None:
        env = default_environment()
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {}

    def test_optional_argument_empty(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": ""}

    def test_any_argument_empty(self) -> None:
        env = default_environment()
        args = parse_args(env, [("foo", int, Multiplicity.ANY)])
        assert args == {"foo": []}

    def test_any_argument(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "123")
        self.add_path_argument(env, "foo", "456")
        self.add_path_argument(env, "foo", "789")
        args = parse_args(env, [("foo", int, Multiplicity.ANY)])
        assert args == {"foo": [123, 456, 789]}

    def test_required_any_argument(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "123")
        self.add_path_argument(env, "foo", "456")
        self.add_path_argument(env, "foo", "789")
        args = parse_args(env, [("foo", int, Multiplicity.REQUIRED_ANY)])
        assert args == {"foo": [123, 456, 789]}

    def test_required_any_argument_missing(self) -> None:
        env = default_environment()
        try:
            parse_args(env, [("foo", int, Multiplicity.REQUIRED_ANY)])
        except ArgumentsError as exc:
            assert exc.arguments == {"foo": "mandatory argument missing"}
        else:
            pytest.fail("ArgumentsError not raised")

    def test_urlencoded_post_request(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_urlencoded_request(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": "bar"}

    def test_urlencoded_post_request_with_umlauts(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_urlencoded_request(env, "föo", "bär")
        args = parse_args(env, [("föo", str, Multiplicity.OPTIONAL)])
        assert args == {"föo": "bär"}

    def test_urlencoded_patch_request(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PATCH"
        self.setup_urlencoded_request(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": "bar"}

    def test_urlencoded_delete_request(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "DELETE"
        self.setup_urlencoded_request(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": "bar"}

    def test_empty_delete__optional(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "DELETE"
        self.setup_empty_urlencoded_request(env)
        args = parse_args(
            env,
            [
                ("opt", str, Multiplicity.OPTIONAL),
                ("any", str, Multiplicity.ANY),
            ],
        )
        assert "opt" not in args
        assert args["any"] == []

    def test_empty_delete__required_not_supplied(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "DELETE"
        self.setup_empty_urlencoded_request(env)
        with pytest.raises(ArgumentsError):
            parse_args(
                env,
                [
                    ("req", str, Multiplicity.REQUIRED),
                    ("once", str, Multiplicity.REQUIRED_ANY),
                ],
            )

    def test_urlencoded_put_request(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PUT"
        self.setup_urlencoded_request(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": "bar"}

    def test_urlencoded_put_request_with_umlauts(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PUT"
        self.setup_urlencoded_request(env, "föo", "bär")
        args = parse_args(env, [("föo", str, Multiplicity.OPTIONAL)])
        assert args == {"föo": "bär"}

    def test_multipart_post_request(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": "bar"}

    def test_multipart_post_request_with_umlauts(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request(env, "föo", "bär")
        args = parse_args(env, [("föo", str, Multiplicity.OPTIONAL)])
        assert args == {"föo": "bär"}

    def test_multipart_put_request(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request(env, "foo", "bar")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": "bar"}

    def test_multipart_put_request_with_umlauts(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request(env, "föo", "bär")
        args = parse_args(env, [("föo", str, Multiplicity.OPTIONAL)])
        assert args == {"föo": "bär"}

    def test_multipart_multiple_arguments(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request(env, "foo", ["bar", "baz"])
        args = parse_args(env, [("foo", str, Multiplicity.ANY)])
        assert args == {"foo": ["bar", "baz"]}

    def test_multipart__optional_argument_empty(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_request(env, "foo", "")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {"foo": ""}

    def test_multipart_post_request_with_file(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            env,
            "my-file",
            "my-file.txt",
            "content",
            "text/plain; charset=us-ascii",
        )
        args = parse_args(env, [("my-file", "file", Multiplicity.REQUIRED)])
        assert "my-file" in args
        f = args["my-file"]
        assert f.filename == "my-file.txt"
        assert f.content_type == "text/plain"
        assert f.read() == b"content"

    def test_multipart_post_request_with_optional_file(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            env,
            "my-file",
            "my-file.txt",
            "content",
            "text/plain; charset=us-ascii",
        )
        args = parse_args(
            env, [("my-file", "file-or-str", Multiplicity.REQUIRED)]
        )
        assert "my-file" in args
        f = args["my-file"]
        assert f.filename == "my-file.txt"
        assert f.content_type == "text/plain"
        assert f.read() == b"content"

    def test_multipart_post_request_with_empty_file(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_request(env, "my-file", "test")
        args = parse_args(
            env, [("my-file", "file-or-str", Multiplicity.REQUIRED)]
        )
        assert "my-file" in args
        assert args["my-file"] == "test"

    def test_multipart_post_request_with_file_and_umlauts(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            env, "föo", "my-filé.txt", "cöntent", "text/plain; charset=utf-8"
        )
        args = parse_args(env, [("föo", "file", Multiplicity.REQUIRED)])
        assert "föo" in args
        f = args["föo"]
        assert f.filename == "my-filé.txt"
        assert f.content_type == "text/plain"
        assert f.read() == "cöntent".encode("utf-8")

    def test_multipart_put_request_with_file(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PUT"
        self.setup_multipart_file_request(
            env, "my-file", "my-file.txt", "content", "text/plain"
        )
        args = parse_args(env, [("my-file", "file", Multiplicity.REQUIRED)])
        assert "my-file" in args
        f = args["my-file"]
        assert f.filename == "my-file.txt"
        assert f.content_type == "text/plain"
        assert f.read() == b"content"

    def test_read_file_as_value(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        self.setup_multipart_file_request(
            env, "foo", "my-file.txt", "123", "text/plain"
        )
        args = parse_args(env, [("foo", int, Multiplicity.REQUIRED)])
        assert args["foo"] == 123

    def test_read_value_as_file(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "GET"
        self.add_path_argument(env, "foo", "bar")
        args = parse_args(env, [("foo", "file", Multiplicity.REQUIRED)])
        assert "foo" in args
        f = args["foo"]
        assert f.filename == ""
        assert f.content_type == "application/octet-stream"
        assert f.read() == b"bar"

    def test_read_value_as_file_with_umlauts(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "GET"
        self.add_path_argument(env, "foo", "bär")
        args = parse_args(env, [("foo", "file", Multiplicity.REQUIRED)])
        assert "foo" in args
        f = args["foo"]
        assert f.filename == ""
        assert f.content_type == "application/octet-stream"
        assert f.read() == "bär".encode("utf-8")

    def test_post_wrong_content_type__optional_args(self) -> None:
        """This exposes a bug in Python's cgi module that will raise a
        TypeError when no request string was provided. See
        <https://github.com/python/cpython/issues/76210>.
        """
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        env["CONTENT_TYPE"] = "application/octet-stream"
        env["CONTENT_LENGTH"] = "2"
        env["wsgi.input"] = BytesIO(b"AB")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {}

    def test_post_wrong_content_type__required_args(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "POST"
        env["CONTENT_TYPE"] = "application/octet-stream"
        env["CONTENT_LENGTH"] = "2"
        env["wsgi.input"] = BytesIO(b"AB")
        with pytest.raises(BadRequest):
            parse_args(env, [("foo", str, Multiplicity.REQUIRED)])

    def test_patch_wrong_content_type__optional_args(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PATCH"
        env["CONTENT_TYPE"] = "application/octet-stream"
        env["CONTENT_LENGTH"] = "2"
        env["wsgi.input"] = BytesIO(b"AB")
        args = parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])
        assert args == {}

    def test_patch_wrong_content_type__required_args(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "PATCH"
        env["CONTENT_TYPE"] = "application/octet-stream"
        env["CONTENT_LENGTH"] = "2"
        env["wsgi.input"] = BytesIO(b"AB")
        with pytest.raises(BadRequest):
            parse_args(env, [("foo", str, Multiplicity.REQUIRED)])

    def test_no_exhaustive_check(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "v")
        self.add_path_argument(env, "unknown", "v")
        # does not raise ArgumentsError
        parse_args(env, [("foo", str, Multiplicity.OPTIONAL)])

    def test_exhaustive_check__succeeds(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "v")
        # does not raise ArgumentsError
        parse_args(
            env,
            [("foo", str, Multiplicity.OPTIONAL)],
            exhaustive=True,
        )

    def test_exhaustive_check__fails(self) -> None:
        env = default_environment()
        self.add_path_argument(env, "foo", "v")
        self.add_path_argument(env, "unknown", "v")
        try:
            parse_args(
                env,
                [("foo", str, Multiplicity.OPTIONAL)],
                exhaustive=True,
            )
        except ArgumentsError as exc:
            assert exc.arguments == {"unknown": "unknown argument"}
        else:
            pytest.fail("ArgumentsError not raised")

    def test_unsupported_method(self) -> None:
        env = default_environment()
        env["REQUEST_METHOD"] = "UNKNOWN"
        with pytest.raises(ValueError):
            parse_args(env, [])


class TestArgumentParser:
    def test_parse_args__post_twice(self) -> None:
        environ = {
            "wsgi.input": BytesIO(b"foo=bar&abc=def"),
            "REQUEST_METHOD": "POST",
            "CONTENT_LENGTH": "15",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
        }
        parser = ArgumentParser(environ)
        args1 = parser.parse_args([("foo", str, Multiplicity.REQUIRED)])
        assert args1 == {"foo": "bar"}
        args2 = parser.parse_args(
            [
                ("foo", str, Multiplicity.REQUIRED),
                ("abc", str, Multiplicity.REQUIRED),
            ]
        )
        assert args2 == {"foo": "bar", "abc": "def"}

    def test_exhaustive_with_previous_calls(self) -> None:
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
        # does not raise ArgumentsError
        parser.parse_args(
            [("abc", str, Multiplicity.REQUIRED)], exhaustive=True
        )
