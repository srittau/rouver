from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from io import BytesIO
from typing import IO, Any, Callable, Dict, Tuple, Union
from urllib.parse import parse_qs

from typing_extensions import Literal
from werkzeug.datastructures import FileStorage, MultiDict
from werkzeug.formparser import parse_form_data

from rouver.exceptions import ArgumentsError
from rouver.types import WSGIEnvironment


class Multiplicity(Enum):
    ANY = "0+"
    REQUIRED_ANY = "1+"
    REQUIRED = "1"
    OPTIONAL = "0-1"


ArgumentValueParser = Callable[[str], Any]
ArgumentValueType = Union[ArgumentValueParser, Literal["file", "file-or-str"]]
ArgumentTemplate = Tuple[str, ArgumentValueType, Multiplicity]
ArgumentDict = Dict[str, Any]

_GET_METHODS = ["GET", "HEAD"]
_FORM_METHODS = ["POST", "PUT", "PATCH", "DELETE"]


class _ArgumentError(Exception):
    pass


class FileArgument:
    """File argument result.

    This is a file-like object, containing a byte stream. It has additional
    fields "filename" and "content_type".

    >>> args = parse_args(..., [
    ...     ("file-arg", "file", Multiplicity.REQUIRED),
    ... ])
    >>> args["file-arg"].filename
    'my-file.txt'
    >>> args["file-arg"].content_type
    'text/plain'
    >>> args["file-arg"].read()
    b'file content'
    """

    def __init__(
        self, stream: IO[bytes], filename: str, content_type: str
    ) -> None:
        self._stream = stream
        self.filename = filename
        self.content_type = content_type

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class ArgumentParser:
    """Parse CGI/WSGI arguments.

    As opposed to parse_args(), ArgumentParser.parse_args() can be called
    multiple times on the same instance during an request.
    """

    def __init__(self, environ: WSGIEnvironment) -> None:
        self.environ = environ

        method: str = environ.get("REQUEST_METHOD", "GET")
        args: MultiDict[str, Any]
        files: MultiDict[str, Any]
        if method in _GET_METHODS:
            qs: str = environ.get("QUERY_STRING", "")
            args = MultiDict(parse_qs(qs, keep_blank_values=True))
            files = MultiDict()
        elif method in _FORM_METHODS:
            _, args, files = parse_form_data(environ)
        else:
            raise ValueError("unsupported method: '{}'".format(method))
        self._arguments = _create_arg_dict(args, files)
        self._not_found = {a for a in self._arguments}

    def parse_args(
        self,
        argument_template: Sequence[ArgumentTemplate],
        *,
        exhaustive: bool = False,
    ) -> ArgumentDict:
        """Parse CGI/WSGI arguments and return an argument dict.

        argument_template is a list of (argname, value_parser, multiplicity)
        tuples. argname is the argument name that is expected to be provided.

        If multiplicity is REQUIRED and the argument was not supplied, an
        ArgumentsError is raised. If multiplicity is OPTIONAL and the
        argument was not supplied, the returned dict does not contain a key
        for this argument. multiplicity can also be ANY, in which case
        the key may be supplied any number of times, or REQUIRED_ANY, which
        works like ANY, but requires the argument to be provided at least
        once.

        value_parser is a callable that takes a single string argument. The
        value returned by this function will be used as the value of the
        returned dict. If the supplied string or list can't be parsed, this
        function should raise a ValueError exception. In this case, parse_args
        raises an ArgumentsError. If value_func is the string "file",
        the value of the argument is a FileArgument instance. If value_func
        is "file-or-str", the value is a FileArgument instance or a str
        if the argument was given, but without a file as argument.

        The returned dict contains the names of all parsed arguments that were
        present in the CGI arguments as key. The value is the corresponding
        parsed argument value. In the case of ANY and REQUIRED_ANY arguments,
        the value is a list of parsed arguments values. Each ANY argument
        has an entry in the dict, even if the argument was not supplied.
        In this case the value is the empty list.

        Arguments of HEAD and GET requests will be parsed from the query
        string, while arguments of POST, PUT, PATCH, and DELETE requests
        are parsed from the request body. Other methods are not supported.

        If the exhaustive argument is set to True and the request contains
        arguments not listed in the argument_template of this or previous
        calls, raise an ArgumentsError.

        If there is any error while parsing the arguments, an ArgumentsError
        will be raised.

        parse_args() consumes the request input, but the arguments are
        cached in the ArgumentParser object, so multiple calls on the same
        object are possible.
        """

        errors: dict[str, str] = {}
        parsed_arguments: ArgumentDict = {}

        def parse_template(
            name: str,
            value_parser: ArgumentValueType,
            multiplicity: Multiplicity,
        ) -> None:
            cls = _VALUE_PARSER_CLASSES[multiplicity]
            argument_parser = cls(self._arguments, name, value_parser)
            if argument_parser.should_parse():
                try:
                    parsed_arguments[name] = argument_parser.parse()
                except _ArgumentError as exc:
                    errors[name] = exc.args[0]
            self._not_found.discard(name)

        for tmpl in argument_template:
            parse_template(*tmpl)

        if exhaustive:
            for arg in self._not_found:
                errors[arg] = "unknown argument"

        if len(errors) > 0:
            raise ArgumentsError(errors)
        return parsed_arguments


class _Argument:
    def __init__(
        self, value: list[str] | FileStorage, *, is_file: bool = False
    ) -> None:
        self._value = value
        self.is_file = is_file

    def as_string(self) -> str:
        if not isinstance(self._value, list) or len(self._value) == 0:
            raise TypeError("value is not a string")
        return self._value[0]

    def as_list(self) -> list[str]:
        if not isinstance(self._value, list):
            raise TypeError("value is not a list of strings")
        return self._value

    def as_file(self) -> tuple[IO[bytes], str, str]:
        if not isinstance(self._value, FileStorage):
            raise TypeError("value is not a file")
        content_type = self._value.mimetype or "application/octet-stream"
        return self._value.stream, self._value.filename or "", content_type


def _create_arg_dict(
    args: MultiDict, files: MultiDict
) -> dict[str, _Argument]:
    _all_args: dict[str, _Argument] = {}
    for name, v in args.lists():
        _all_args[name] = _Argument(v)
    for name, v in files.items():
        _all_args[name] = _Argument(v, is_file=True)
    return _all_args


def parse_args(
    environ: WSGIEnvironment,
    argument_template: Sequence[ArgumentTemplate],
    *,
    exhaustive: bool = False,
) -> ArgumentDict:
    """Parse CGI/WSGI arguments and return an argument dict.

    argument_template is a list of (argname, value_parser, multiplicity)
    tuples. argname is the argument name that is expected to be provided.

    If multiplicity is REQUIRED and the argument was not supplied, an
    ArgumentsError is raised. If multiplicity is OPTIONAL and the
    argument was not supplied, the returned dict does not contain a key
    for this argument. multiplicity can also be ANY, in which case
    the key may be supplied any number of times, or REQUIRED_ANY, which works
    like ANY, but requires the argument to be provided at least once.

    value_parser is a callable that takes a single string argument. The value
    returned by this function will be used as the value of the returned
    dict. If the supplied string or list can't be parsed, this function
    should raise a ValueError exception. In this case, parse_args raises
    an ArgumentsError. If value_func is the string "file", the value of the
    argument is a FileArgument instance. If value_func is "file-or-str",
    the value is a FileArgument instance or a str if the argument was given,
    but without a file as argument.

    The returned dict contains the names of all parsed arguments that were
    present in the CGI arguments as key. The value is the corresponding
    parsed argument value. In the case of ANY and REQUIRED_ANY arguments,
    the value is a list of parsed arguments values. Each ANY argument has an
    entry in the dict, even if the argument was not supplied. In this case the
    value is the empty list.

    Arguments of HEAD and GET requests will be parsed from the query string,
    while arguments of POST, PUT, PATCH, and DELETE requests are parsed from
    the request body. Other methods are not supported.

    If the exhaustive argument is set to True and the request contains
    arguments not listed in the argument_template, raise an ArgumentsError.

    If there is any error while parsing the arguments, an ArgumentsError
    will be raised.

    >>> from io import StringIO
    >>> environment = {
    ...     "QUERY_STRING": "key=value&multi=1&multi=2",
    ...     "wsgi.input": StringIO(""),
    ... }
    >>> args = parse_args(environment, [
    ...     ("key", str, Multiplicity.REQUIRED),
    ...     ("multi", int, Multiplicity.ANY),
    ...     ("optional", str, Multiplicity.OPTIONAL),
    ... ])
    >>> args["key"]
    'value'
    >>> args["multi"]
    [1, 2]
    >>> "optional" in args
    False
    >>> parse_args(environment, [("key", int, Multiplicity.REQUIRED)])
    Traceback (most recent call last):
    ...
    ArgumentsError: 400 Bad Request
    >>> parse_args(environment, [("missing", str, Multiplicity.REQUIRED)])
    Traceback (most recent call last):
    ...
    ArgumentsError: 400 Bad Request
    >>> parse_args(
    ...     environment, [("multi", str, Multiplicity.ANY)], exhaustive=True
    ... )
    Traceback (most recent call last):
    ...
    ArgumentsError: 400 Bad Request

    parse_args() consumes the request input, so multiple calls per request
    are not possible.
    """

    parser = ArgumentParser(environ)
    return parser.parse_args(argument_template, exhaustive=exhaustive)


class _ValueParserWrapper:
    def parse_from_string(self, s: str) -> Any:
        raise NotImplementedError()

    def parse_from_file(
        self, stream: IO[bytes], filename: str, content_type: str
    ) -> Any:
        raise NotImplementedError()


class _FunctionValueParser(_ValueParserWrapper):
    def __init__(self, value_parser: ArgumentValueParser) -> None:
        super().__init__()
        self.value_parser = value_parser

    def parse_from_string(self, value: str) -> Any:
        try:
            return self.value_parser(value)
        except ValueError as exc:
            raise _ArgumentError(str(exc)) from exc

    def parse_from_file(
        self, stream: IO[bytes], filename: str, content_type: str
    ) -> Any:
        return self.parse_from_string(stream.read().decode("utf-8"))


class _FileArgumentValueParser(_ValueParserWrapper):
    def parse_from_string(self, value: str) -> FileArgument:
        stream = BytesIO(value.encode("utf-8"))
        return FileArgument(stream, "", "application/octet-stream")

    def parse_from_file(
        self, stream: IO[bytes], filename: str, content_type: str
    ) -> FileArgument:
        return FileArgument(stream, filename, content_type)


class _OptionalFileArgumentValueParser(_ValueParserWrapper):
    def parse_from_string(self, value: str) -> str:
        return value

    def parse_from_file(
        self, stream: IO[bytes], filename: str, content_type: str
    ) -> FileArgument:
        return FileArgument(stream, filename, content_type)


def _create_argument_value_parser(
    value_parser: ArgumentValueType,
) -> _ValueParserWrapper:
    if value_parser == "file":
        return _FileArgumentValueParser()
    elif value_parser == "file-or-str":
        return _OptionalFileArgumentValueParser()
    elif callable(value_parser):
        return _FunctionValueParser(value_parser)
    else:
        raise TypeError("invalid value parser '{}'".format(value_parser))


class _ArgumentParser:
    def __init__(
        self,
        args: dict[str, _Argument],
        name: str,
        value_parser: ArgumentValueType,
    ) -> None:
        self.args = args
        self.name = name
        self.value_parser = _create_argument_value_parser(value_parser)

    def should_parse(self) -> bool:
        return True

    def parse(self) -> Any:
        raise NotImplementedError()


class _SingleArgumentParser(_ArgumentParser):
    def parse(self) -> Any:
        raise NotImplementedError()

    def parse_single_arg(self) -> Any:
        arg = self.args[self.name]
        if arg.is_file:
            stream, filename, content_type = arg.as_file()
            return self.value_parser.parse_from_file(
                stream, filename, content_type
            )
        else:
            value = arg.as_string()
            return self.value_parser.parse_from_string(value)

    @property
    def arg_supplied(self) -> bool:
        try:
            return self.name in self.args
        except TypeError:
            return False


class _RequiredArgumentParser(_SingleArgumentParser):
    def parse(self) -> Any:
        if not self.arg_supplied:
            raise _ArgumentError("mandatory argument missing")
        return self.parse_single_arg()


class _OptionalArgumentParser(_SingleArgumentParser):
    def should_parse(self) -> bool:
        return self.arg_supplied

    def parse(self) -> Any:
        assert self.should_parse()
        return self.parse_single_arg()


class _MultiArgumentParser(_ArgumentParser):
    def parse(self) -> list[Any]:
        try:
            arg = self.args[self.name]
            values = arg.as_list()
        except KeyError:
            values = []
        return [self.value_parser.parse_from_string(v) for v in values]


class _AtLeastOneArgumentParser(_MultiArgumentParser):
    def parse(self) -> list[Any]:
        values = super().parse()
        if not values:
            raise _ArgumentError("mandatory argument missing")
        return values


_VALUE_PARSER_CLASSES = {
    Multiplicity.ANY: _MultiArgumentParser,
    Multiplicity.REQUIRED_ANY: _AtLeastOneArgumentParser,
    Multiplicity.REQUIRED: _RequiredArgumentParser,
    Multiplicity.OPTIONAL: _OptionalArgumentParser,
}
