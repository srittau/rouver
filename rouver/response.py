from http import HTTPStatus
from json import dumps as dumps_json
from typing import Union, Any, Iterator, Sequence
from urllib.parse import quote

from werkzeug.wrappers import Request

from rouver.html import created_at_page, see_other_page, \
    temporary_redirect_page
from rouver.status import status_line
from rouver.types import StartResponse, Header


_JSON_HEADER = ("Content-Type", "application/json; charset=utf-8")


def _absolute_url(request: Request, url_part: str) -> str:
    if url_part.startswith("/"):
        url_part = url_part[1:]
    return request.host_url + quote(url_part)


def _location_header(request: Request, url_part: str) -> Header:
    return "Location", _absolute_url(request, url_part)


def respond(start_response: StartResponse, *,
            status: HTTPStatus = HTTPStatus.OK,
            extra_headers: Sequence[Header] = []) -> Iterator[bytes]:

    """Prepare an empty WSGI response.

    >>> def handler(start_response, request):
    ...     return respond(start_response, status=HTTPStatus.ACCEPTED)

    The return value can be ignored to return an arbitrary response body.

    >>> def handler(start_response, request):
    ...     respond(start_response,
    ...             extra_headers=[("Content-Type", "text/plain")])
    ...     return [b"My Response"]
    """

    sl = status_line(status)
    start_response(sl, extra_headers)
    return iter([])


def respond_with_json(start_response: StartResponse,
                      json: Union[str, bytes, Any], *,
                      status: HTTPStatus = HTTPStatus.OK,
                      extra_headers: Sequence[Header] = []) \
        -> Iterator[bytes]:

    """Prepare a JSON WSGI response.

    >>> def handler(start_response, request):
    ...     return respond_with_json(start_response, {"foo": "bar"})

    The JSON text to return can be supplied as a string, as an UTF-8-encoded
    bytestring, or as any object that can be serialized using json.dumps().

    The default response status of "200 OK" can be overridden with the
    "status" keyword argument.
    """

    sl = status_line(status)
    headers = [_JSON_HEADER] + list(extra_headers)
    start_response(sl, headers)
    if isinstance(json, bytes):
        encoded = json
    elif isinstance(json, str):
        encoded = json.encode("utf-8")
    else:
        encoded = dumps_json(json).encode("utf-8")
    return iter([encoded])


def respond_with_html(start_response: StartResponse, html: str, *,
                      status: HTTPStatus = HTTPStatus.OK,
                      extra_headers: Sequence[Header] = []) \
        -> Iterator[bytes]:

    """Prepare an HTML WSGI response.

    >>> def handler(start_response, request):
    ...     return respond_with_html(start_response, "<div>foo</div>")

    The default response status of "200 OK" can be overridden with the
    "status" keyword argument.
    """

    sl = status_line(status)
    headers = \
        [("Content-Type", "text/html; charset=utf-8")] + list(extra_headers)
    start_response(sl, headers)
    return iter([html.encode("utf-8")])


def created_at(request: Request, start_response: StartResponse,
               url_part: str) -> Iterator[bytes]:

    """Prepare a 201 Created WSGI response with a Location header.

    The default content-type is "text/html" and the return value generates
    a simple HTML body.
    """

    url = _absolute_url(request, url_part)
    html = created_at_page(url)
    return respond_with_html(
        start_response, html, status=HTTPStatus.CREATED,
        extra_headers=[_location_header(request, url_part)])


def created_as_json(request: Request, start_response: StartResponse,
                    url_part: str, json: Union[str, bytes, Any]) \
        -> Iterator[bytes]:
    """Prepare a 201 Created WSGI response with a Location header and JSON body.
    """

    return respond_with_json(
        start_response, json, status=HTTPStatus.CREATED, extra_headers=[
            _location_header(request, url_part),
        ])


def temporary_redirect(request: Request, start_response: StartResponse,
                       url_part: str) -> Iterator[bytes]:
    url = _absolute_url(request, url_part)
    html = temporary_redirect_page(url)
    return respond_with_html(
        start_response, html, status=HTTPStatus.TEMPORARY_REDIRECT,
        extra_headers=[
            _location_header(request, url_part),
        ])


def see_other(request: Request, start_response: StartResponse,
              url_part: str) -> Iterator[bytes]:
    url = _absolute_url(request, url_part)
    html = see_other_page(url)
    return respond_with_html(
        start_response, html, status=HTTPStatus.SEE_OTHER,
        extra_headers=[_location_header(request, url_part)])
