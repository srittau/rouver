from http import HTTPStatus
from typing import Iterable

from rouver.status import status_line
from rouver.types import StartResponseType


def respond_with_html(start_response: StartResponseType, html: str, *,
                      status: HTTPStatus = HTTPStatus.OK) \
        -> Iterable[bytes]:

    """Prepare an HTML WSGI response.

    >>> def handler(start_response, request):
    ...     return respond_with_html(start_response, "<div>foo</div>")

    The default response status of "200 OK" can be overridden with the
    "status" keyword argument.
    """

    sl = status_line(status)
    start_response(sl, [("Content-Type", "text/html; charset=utf-8")])
    return [html.encode("utf-8")]
