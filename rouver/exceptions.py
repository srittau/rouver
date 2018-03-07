from werkzeug.exceptions import BadRequest

from rouver.types import BadArgumentsDict


class ArgumentsError(BadRequest):
    """One or more CGI or JSON arguments were invalid.

    Requires a dictionary as argument, where keys are the argument names or
    JSON paths that have errors, and the values are messages describing the
    problem.

    >>> error = ArgumentsError({
    ...     "foo": "argument missing",
    ...     "bar": "int required, got 'baz'",
    ... })
    >>> len(error.arguments)
    2

    """

    def __init__(self, arguments: BadArgumentsDict) -> None:
        super().__init__("invalid arguments")
        self.arguments = dict(arguments)
