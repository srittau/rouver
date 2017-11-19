import collections
from http import HTTPStatus
from typing import cast, Any, Union, Iterator, Sequence, Dict

from werkzeug.wrappers import Request

from rouver.args import ArgumentTemplate, ArgumentDict, parse_args
from rouver.response import \
    respond, respond_with_json, respond_with_html, created_at, see_other, \
    created_as_json, temporary_redirect
from rouver.types import StartResponse, Header


class RouteHandlerBase(collections.Iterable):

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

    def __init__(self, request: Request, path_args: Sequence[Any],
                 start_response: StartResponse) -> None:
        self.request = request
        self.path_args = path_args
        self.start_response = start_response

    def __iter__(self) -> Iterator[bytes]:
        raise NotImplementedError()

    def parse_args(self, argument_template: Sequence[ArgumentTemplate]) \
            -> ArgumentDict:
        return parse_args(cast(Dict[str, Any], self.request.environ),
                          argument_template)

    def respond(self, extra_headers: Sequence[Header] = []) \
            -> Iterator[bytes]:
        return respond(self.start_response, extra_headers=extra_headers)

    def respond_with_json(
            self, json: Union[str, bytes, Any], *,
            status: HTTPStatus = HTTPStatus.OK,
            extra_headers: Sequence[Header] = []) -> Iterator[bytes]:
        return respond_with_json(
            self.start_response, json,
            status=status, extra_headers=extra_headers)

    def respond_with_html(
            self, html: str, *, status: HTTPStatus = HTTPStatus.OK,
            extra_headers: Sequence[Header] = []) \
            -> Iterator[bytes]:
        return respond_with_html(
            self.start_response, html,
            status=status, extra_headers=extra_headers)

    def created_at(self, url_part: str) -> Iterator[bytes]:
        return created_at(self.request, self.start_response, url_part)

    def created_as_json(self, url_part: str, json: Union[str, bytes, Any]) \
            -> Iterator[bytes]:
        return created_as_json(
            self.request, self.start_response, url_part, json)

    def temporary_redirect(self, url_part: str) -> Iterator[bytes]:
        return temporary_redirect(self.request, self.start_response, url_part)

    def see_other(self, url_part: str) -> Iterator[bytes]:
        return see_other(self.request, self.start_response, url_part)
