import cgi
from enum import Enum
from io import BytesIO
from typing import Callable, Any, Tuple, Dict, List, Union, IO, Sequence

from werkzeug.exceptions import BadRequest

from rouver.exceptions import ArgumentsError
from rouver.types import WSGIEnvironment


class Multiplicity(Enum):

    ANY = "0+"
    REQUIRED_ANY = "1+"
    REQUIRED = "1"
    OPTIONAL = "0-1"


ArgumentValueParser = Callable[[str], Any]
ArgumentValueType = Union[ArgumentValueParser, str]
ArgumentTemplate = Tuple[str, ArgumentValueType, Multiplicity]
ArgumentDict = Dict[str, Any]


_FORM_TYPES = ["application/x-www-form-urlencoded", "multipart/form-data"]


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

    def __init__(self, stream: IO[bytes], filename: str, content_type: str) \
            -> None:
        self._stream = stream
        self.filename = filename
        self.content_type = content_type

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class CGIFileArgument(FileArgument):

    def __init__(self, value: cgi.FieldStorage) -> None:
        content_type = value.headers.get(
            "content-type", "application/octet-stream").split(";")[0]
        assert value.file is not None
        assert value.filename is not None
        super().__init__(value.file, value.filename, content_type)
        # We keep a reference to the FieldStorage around, otherwise the
        # file will get closed in FieldStorage.__del__().
        self._value = value


def parse_args(environment: WSGIEnvironment,
               argument_template: Sequence[ArgumentTemplate]) -> ArgumentDict:

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
    argument is a FileArgument instance.

    The returned dict contains the names of all parsed arguments that were
    present in the CGI arguments as key. The value is the corresponding
    parsed argument value. In the case of ANY and REQUIRED_ANY arguments,
    the value is a list of parsed arguments values. Each ANY argument has an
    entry in the dict, even if the argument was not supplied. In this case the
    value is the empty list.

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
    >>>

    """

    def has_wrong_content_type() -> bool:
        method = environment.get("REQUEST_METHOD", "GET")
        if method.upper() not in ["POST", "PUT"]:
            return False
        content_type = environment.get("CONTENT_TYPE", "").split(";")[0]
        return content_type not in _FORM_TYPES

    if has_wrong_content_type():
        raise BadRequest("incorrect content type, expected {}".format(
            " or ".join(_FORM_TYPES)))

    arguments = cgi.FieldStorage(
        environment["wsgi.input"], environ=environment,
        keep_blank_values=True)

    errors = {}  # type: Dict[str, str]
    parsed_arguments = {}  # type: ArgumentDict

    def parse_template(name: str, value_parser: ArgumentValueType,
                       multiplicity: Multiplicity) -> None:
        cls = _VALUE_PARSER_CLASSES[multiplicity]
        argument_parser = cls(arguments, name, value_parser)
        if argument_parser.should_parse():
            try:
                parsed_arguments[name] = argument_parser.parse()
            except _ArgumentError as exc:
                errors[name] = exc.args[0]

    for tmpl in argument_template:
        parse_template(*tmpl)

    if len(errors) > 0:
        raise ArgumentsError(errors)
    return parsed_arguments


class _ValueParserWrapper:

    def parse_from_string(self, s: str) -> Any:
        raise NotImplementedError()

    def parse_from_file(self, value: cgi.FieldStorage) -> Any:
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

    def parse_from_file(self, value: cgi.FieldStorage) -> Any:
        assert value.file is not None
        content = value.file.read()
        decoded = \
            content.decode("utf-8") if isinstance(content, bytes) else content
        return self.parse_from_string(decoded)


class _FileArgumentValueParser(_ValueParserWrapper):

    def parse_from_string(self, value: str) -> FileArgument:
        stream = BytesIO(value.encode("utf-8"))
        return FileArgument(stream, "", "application/octet-stream")

    def parse_from_file(self, value: cgi.FieldStorage) -> CGIFileArgument:
        return CGIFileArgument(value)


def _create_argument_value_parser(value_parser: ArgumentValueType) \
        -> _ValueParserWrapper:
    if value_parser == "file":
        return _FileArgumentValueParser()
    elif callable(value_parser):
        return _FunctionValueParser(value_parser)
    else:
        raise TypeError("invalid value parser '{}'".format(value_parser))


class _ArgumentParser:

    def __init__(self, args: cgi.FieldStorage, name: str,
                 value_parser: ArgumentValueType) -> None:
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
        if self.is_argument_a_file:
            file = self.args[self.name]
            return self.value_parser.parse_from_file(file)
        else:
            value = self.args.getfirst(self.name)
            return self.value_parser.parse_from_string(value)

    @property
    def is_argument_a_file(self) -> bool:
        argv = self.args[self.name]
        return hasattr(argv, "file") and argv.file is not None


class _RequiredArgumentParser(_SingleArgumentParser):

    def parse(self) -> Any:
        if self.name not in self.args:
            raise _ArgumentError("mandatory argument missing")
        return self.parse_single_arg()


class _OptionalArgumentParser(_SingleArgumentParser):

    def should_parse(self) -> bool:
        if self.name not in self.args:
            return False
        return True

    def parse(self) -> Any:
        assert self.should_parse()
        return self.parse_single_arg()


class _MultiArgumentParser(_ArgumentParser):

    def parse(self) -> List[Any]:
        values = self.args.getlist(self.name)
        return [self.value_parser.parse_from_string(v) for v in values]


class _AtLeastOneArgumentParser(_MultiArgumentParser):

    def parse(self) -> List[Any]:
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
