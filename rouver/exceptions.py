from typing import Dict

from werkzeug.exceptions import BadRequest


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

    def __init__(self, arguments: Dict[str, str]) -> None:
        super().__init__("invalid arguments")
        self.arguments = arguments
