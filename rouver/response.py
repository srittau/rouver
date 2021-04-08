from __future__ import annotations

from collections.abc import Iterable, Sequence
from http import HTTPStatus
from json import dumps as dumps_json
from typing import Any

from werkzeug.wrappers import Request

from rouver.html import (
    created_at_page,
    see_other_page,
    temporary_redirect_page,
)
from rouver.status import status_line
from rouver.types import Header, StartResponse
from rouver.util import absolute_url


def _location_header(request: Request, url: str) -> Header:
    return "Location", absolute_url(request, url)


def respond(
    start_response: StartResponse,
    *,
    status: HTTPStatus = HTTPStatus.OK,
    content_type: str | None = None,
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    """Prepare an empty WSGI response.

    >>> def handler(start_response, request):
    ...     return respond(start_response, status=HTTPStatus.ACCEPTED)

    The return value can be ignored to return an arbitrary response body.

    >>> def handler(start_response, request):
    ...     respond(start_response, content_type="text/plain")
    ...     return [b"My Response"]
    """

    sl = status_line(status)
    all_headers = list(extra_headers)
    if content_type is not None:
        if any(h.lower() == "content-type" for (h, _) in extra_headers):
            raise ValueError("duplicate Content-Type header")
        all_headers += [("Content-Type", content_type)]
    start_response(sl, all_headers)
    return []


def respond_with_content(
    start_response: StartResponse,
    content: bytes,
    *,
    status: HTTPStatus = HTTPStatus.OK,
    content_type: str = "application/octet-stream",
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    """Prepare an WSGI response.

    >>> def handler(start_response, request):
    ...     return respond_with_content(start_response, b"content")

    The response will include a Content-Type and a Content-Length header.

    """

    sl = status_line(status)
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(content))),
    ] + list(extra_headers)
    start_response(sl, headers)
    return [content]


def respond_with_json(
    start_response: StartResponse,
    json: str | bytes | Any,
    *,
    status: HTTPStatus = HTTPStatus.OK,
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    """Prepare a JSON WSGI response.

    >>> def handler(start_response, request):
    ...     return respond_with_json(start_response, {"foo": "bar"})

    The JSON text to return can be supplied as a string, as an UTF-8-encoded
    bytestring, or as any object that can be serialized using json.dumps().

    The default response status of "200 OK" can be overridden with the
    "status" keyword argument.
    """

    if isinstance(json, bytes):
        encoded = json
    elif isinstance(json, str):
        encoded = json.encode("utf-8")
    else:
        encoded = dumps_json(json).encode("utf-8")

    return respond_with_content(
        start_response,
        encoded,
        status=status,
        content_type="application/json; charset=utf-8",
        extra_headers=extra_headers,
    )


def respond_with_html(
    start_response: StartResponse,
    html: str,
    *,
    status: HTTPStatus = HTTPStatus.OK,
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    """Prepare an HTML WSGI response.

    >>> def handler(start_response, request):
    ...     return respond_with_html(start_response, "<div>foo</div>")

    The default response status of "200 OK" can be overridden with the
    "status" keyword argument.
    """

    encoded = html.encode("utf-8")
    return respond_with_content(
        start_response,
        encoded,
        status=status,
        content_type="text/html; charset=utf-8",
        extra_headers=extra_headers,
    )


def created_at(
    request: Request,
    start_response: StartResponse,
    url_part: str,
    *,
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    """Prepare a 201 Created WSGI response with a Location header.

    The default content-type is "text/html" and the return value generates
    a simple HTML body.
    """

    url = absolute_url(request, url_part)
    html = created_at_page(url)
    all_headers = [_location_header(request, url_part)] + list(extra_headers)
    return respond_with_html(
        start_response,
        html,
        status=HTTPStatus.CREATED,
        extra_headers=all_headers,
    )


def created_as_json(
    request: Request,
    start_response: StartResponse,
    url_part: str,
    json: str | bytes | Any,
    *,
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    """
    Prepare a 201 Created WSGI response with a Location header and JSON body.
    """

    all_headers = [_location_header(request, url_part)] + list(extra_headers)
    return respond_with_json(
        start_response,
        json,
        status=HTTPStatus.CREATED,
        extra_headers=all_headers,
    )


def temporary_redirect(
    request: Request,
    start_response: StartResponse,
    url_part: str,
    *,
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    url = absolute_url(request, url_part)
    html = temporary_redirect_page(url)
    all_headers = [_location_header(request, url_part)] + list(extra_headers)
    return respond_with_html(
        start_response,
        html,
        status=HTTPStatus.TEMPORARY_REDIRECT,
        extra_headers=all_headers,
    )


def see_other(
    request: Request,
    start_response: StartResponse,
    url_part: str,
    *,
    extra_headers: Sequence[Header] = [],
) -> Iterable[bytes]:
    url = absolute_url(request, url_part)
    html = see_other_page(url)
    all_headers = [_location_header(request, url_part)] + list(extra_headers)
    return respond_with_html(
        start_response,
        html,
        status=HTTPStatus.SEE_OTHER,
        extra_headers=all_headers,
    )
