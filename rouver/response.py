from http import HTTPStatus
from typing import Iterable, List

from werkzeug.wrappers import Request

from rouver.html import see_other_page
from rouver.status import status_line
from rouver.types import StartResponseType, HeaderType


def respond_with_html(start_response: StartResponseType, html: str, *,
                      status: HTTPStatus = HTTPStatus.OK,
                      extra_headers: List[HeaderType] = []) \
        -> Iterable[bytes]:

    """Prepare an HTML WSGI response.

    >>> def handler(start_response, request):
    ...     return respond_with_html(start_response, "<div>foo</div>")

    The default response status of "200 OK" can be overridden with the
    "status" keyword argument.
    """

    sl = status_line(status)
    headers = [("Content-Type", "text/html; charset=utf-8")] + extra_headers
    start_response(sl, headers)
    return iter([html.encode("utf-8")])


def see_other(request: Request, start_response: StartResponseType,
              url_part: str) -> Iterable[bytes]:
    if url_part.startswith("/"):
        url_part = url_part[1:]
    url = request.host_url + url_part
    html = see_other_page(url)
    return respond_with_html(start_response, html, status=HTTPStatus.SEE_OTHER,
                             extra_headers=[("Location", url)])
