from http import HTTPStatus
from typing import List, Any, Iterable, Union

from werkzeug.wrappers import Request

from rouver.args import ArgumentTemplate, ArgumentDict, parse_args
from rouver.response import \
    respond, respond_with_json, respond_with_html, created_at, see_other
from rouver.types import StartResponseType, HeaderType


class RouteHandlerBase:

    """Base class for rouver route handlers.

    Sub-classes of RouteHandlerBase can act as route handlers. They provide
    convenient, opaque access to several rouver services.

    Implementations must implement the __iter__() method.

    >>> from rouver.router import Router
    >>> class MyRouteHandler(RouteHandlerBase):
    ...     def __iter__(self):
    ...         return self.respond_with_html("<div>Hello World!</div>")
    >>> class MyRouter(Router):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.add_routes([
    ...             ("my-route", "GET", MyRouteHandler),
    ...         ])
    """

    def __init__(self, request: Request, path_args: List[Any],
                 start_response: StartResponseType) -> None:
        self.request = request
        self.path_args = path_args
        self.start_response = start_response

    def __iter__(self) -> Iterable[bytes]:
        raise NotImplementedError()

    def parse_args(self, argument_template: List[ArgumentTemplate]) \
            -> ArgumentDict:
        return parse_args(self.request.environ, argument_template)

    def respond(self, extra_headers: List[HeaderType] = []) \
            -> Iterable[bytes]:
        return respond(self.start_response, extra_headers=extra_headers)

    def respond_with_json(
            self, json: Union[str, bytes, Any], *,
            status: HTTPStatus = HTTPStatus.OK,
            extra_headers: List[HeaderType] = []) -> Iterable[bytes]:
        return respond_with_json(
            self.start_response, json,
            status=status, extra_headers=extra_headers)

    def respond_with_html(
            self, html: str, *, status: HTTPStatus = HTTPStatus.OK,
            extra_headers: List[HeaderType] = []) \
            -> Iterable[bytes]:
        return respond_with_html(
            self.start_response, html,
            status=status, extra_headers=extra_headers)

    def created_at(self, url_part: str) -> Iterable[bytes]:
        return created_at(self.request, self.start_response, url_part)

    def see_other(self, url_part: str) -> Iterable[bytes]:
        return see_other(self.request, self.start_response, url_part)
