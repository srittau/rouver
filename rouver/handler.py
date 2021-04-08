from __future__ import annotations

import collections.abc
from collections.abc import Iterable, Iterator, Sequence
from http import HTTPStatus
from json import JSONDecodeError, loads as json_loads
from typing import Any, cast
from urllib.parse import unquote

from werkzeug.exceptions import UnsupportedMediaType
from werkzeug.wrappers import Request

from rouver.args import ArgumentDict, ArgumentParser, ArgumentTemplate
from rouver.response import (
    created_as_json,
    created_at,
    respond,
    respond_with_content,
    respond_with_html,
    respond_with_json,
    see_other,
    temporary_redirect,
)
from rouver.types import Header, StartResponse, WSGIEnvironment


class RouteHandlerBase(collections.abc.Iterable):
    """Base class for rouver route handlers.

    Sub-classes of RouteHandlerBase can act as route handlers. They provide
    convenient, opaque access to several rouver services.

    Implementations must implement the prepare_response() method.

    >>> from rouver.router import Router
    >>> class MyRouteHandler(RouteHandlerBase):
    ...     def prepare_response(self):
    ...         return self.respond_with_html("<div>Hello World!</div>")

    >>> class MyRouter(Router):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.add_routes([
    ...             ("my-route", "GET", MyRouteHandler),
    ...         ])
    """

    def __init__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> None:
        self.request = Request(environ)
        self.start_response = start_response
        self._argument_parser: ArgumentParser | None = None
        self._response = self.prepare_response()

    def __iter__(self) -> Iterator[bytes]:
        return iter(self._response)

    @property
    def _charset(self) -> str:
        return cast(str, self.request.mimetype_params.get("charset", "utf-8"))

    @property
    def path_args(self) -> list[Any]:
        path_args = self.request.environ.get("rouver.path_args")
        if not isinstance(path_args, list):
            return []
        return path_args

    @property
    def wildcard_path(self) -> str:
        path = self.request.environ.get("rouver.wildcard_path")
        if not isinstance(path, str):
            return ""
        return unquote(path)

    def prepare_response(self) -> Iterable[bytes]:
        raise NotImplementedError()

    def parse_args(
        self,
        argument_template: Sequence[ArgumentTemplate],
        *,
        exhaustive: bool = False,
    ) -> ArgumentDict:
        if self._argument_parser is None:
            environ = self.request.environ
            self._argument_parser = ArgumentParser(environ)
        return self._argument_parser.parse_args(
            argument_template, exhaustive=exhaustive
        )

    def parse_json_request(self) -> Any:
        """Parse the request body as JSON.

        Raise UnsupportedMediaType if the content type does not indicate
        a JSON request or if it contains invalid JSON.
        """

        if self.request.mimetype != "application/json":
            raise UnsupportedMediaType()
        try:
            j = self.request.data.decode(self._charset)
            return json_loads(j)
        except (LookupError, JSONDecodeError) as exc:
            raise UnsupportedMediaType(str(exc)) from exc

    def respond(
        self,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str | None = None,
        extra_headers: Sequence[Header] = [],
    ) -> Iterable[bytes]:
        return respond(
            self.start_response,
            status=status,
            content_type=content_type,
            extra_headers=extra_headers,
        )

    def respond_with_content(
        self,
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
        return respond_with_content(
            self.start_response,
            content,
            status=status,
            content_type=content_type,
            extra_headers=extra_headers,
        )

    def respond_with_json(
        self,
        json: str | bytes | Any,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: Sequence[Header] = [],
    ) -> Iterable[bytes]:
        return respond_with_json(
            self.start_response,
            json,
            status=status,
            extra_headers=extra_headers,
        )

    def respond_with_html(
        self,
        html: str,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: Sequence[Header] = [],
    ) -> Iterable[bytes]:
        return respond_with_html(
            self.start_response,
            html,
            status=status,
            extra_headers=extra_headers,
        )

    def created_at(self, url_part: str) -> Iterable[bytes]:
        return created_at(self.request, self.start_response, url_part)

    def created_as_json(
        self, url_part: str, json: str | bytes | Any
    ) -> Iterable[bytes]:
        return created_as_json(
            self.request, self.start_response, url_part, json
        )

    def temporary_redirect(self, url_part: str) -> Iterable[bytes]:
        return temporary_redirect(self.request, self.start_response, url_part)

    def see_other(self, url_part: str) -> Iterable[bytes]:
        return see_other(self.request, self.start_response, url_part)
