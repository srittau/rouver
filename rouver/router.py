from enum import Enum
from http import HTTPStatus
import logging
import re
from typing import cast, Iterable, List, Dict, Any, Tuple, Iterator, Sequence

from werkzeug.exceptions import NotFound, MethodNotAllowed, HTTPException
from werkzeug.wrappers import Request

from rouver.exceptions import ArgumentsError
from rouver.html import http_status_page, bad_arguments_page
from rouver.response import respond_with_html
from rouver.types import StartResponse, WSGIEnvironment, RouteDescription, \
    RouteHandler, RouteTemplateHandler, BadArgumentsDict

LOGGER_NAME = "rouver"


class _TemplatePartType(Enum):

    STATIC = 1
    PATTERN = 2


_TemplateHandlerDict = Dict[str, RouteTemplateHandler]
_RouteTemplatePart = Tuple[_TemplatePartType, str]


def _split_path(s: str) -> List[str]:
    if not s:
        return []
    return s.split("/")


class Router:

    def __init__(self) -> None:
        self._handlers = []  # type: List[_RouteHandler]
        self._template_handlers = {}  # type: _TemplateHandlerDict
        self.error_handling = True

    def __call__(self, environment: WSGIEnvironment,
                 start_response: StartResponse) -> Iterable[bytes]:
        request = Request(environment)
        try:
            return _dispatch(request, start_response, self._handlers,
                             self._template_handlers)
        except Exception:
            if self.error_handling:
                logging.getLogger(LOGGER_NAME).exception(
                    "error while handling request")
                return _respond_internal_server_error(start_response)
            else:
                raise

    def add_routes(self, routes: Sequence[RouteDescription]) -> None:
        self._handlers.extend(
            [_RouteHandler(r, self._template_handlers) for r in routes])

    def add_template_handler(self, name: str, handler: RouteTemplateHandler) \
            -> None:
        self._template_handlers[name] = handler


_pattern_re = re.compile(r"^{(.*)}$")


def _parse_route_template_part(
        part: str, template_handlers: _TemplateHandlerDict) \
        -> _RouteTemplatePart:
    if part == "*":
        raise ValueError("wildcard not at end of path")
    m = _pattern_re.match(part)
    if m:
        name = m.group(1)
        if name not in template_handlers:
            msg = "unknown template path handler: '{}'".format(name)
            raise KeyError(msg) from None
        return _TemplatePartType.PATTERN, name
    else:
        return _TemplatePartType.STATIC, part


class _RouteHandler:

    def __init__(self, route: RouteDescription,
                 template_handlers: _TemplateHandlerDict) -> None:
        self.path, self.wildcard = \
            self._parse_path(route[0], template_handlers)
        self.method = route[1]
        self.handler = route[2]

    @staticmethod
    def _parse_path(path_string: str,
                    template_handlers: _TemplateHandlerDict) \
            -> Tuple[List[_RouteTemplatePart], bool]:
        parts = _split_path(path_string)
        if parts and parts[-1] == "*":
            parts = parts[:-1]
            wildcard = True
        else:
            wildcard = False
        templates = [
            _parse_route_template_part(part, template_handlers)
            for part in parts]
        return templates, wildcard


def _dispatch(request: Request, start_response: StartResponse,
              handlers: Sequence[_RouteHandler],
              template_handlers: _TemplateHandlerDict) -> Iterable[bytes]:

    def find_route_and_call_handler() -> Iterable[bytes]:
        try:
            handler, arguments = find_route()
        except NotFound:
            return _respond_not_found(request, start_response)
        except MethodNotAllowed as exc:
            return _respond_method_not_allowed(
                start_response, request.method, exc.valid_methods)
        else:
            return _call_handler(handler, arguments)

    def find_route() -> Tuple[RouteHandler, List[Any]]:
        arguments = _RouteArguments(request, template_handlers)
        matchers = [
            _RouteMatcher(h, request.path, arguments) for h in handlers]

        matching_paths = [m for m in matchers if m.matches]
        if not matching_paths:
            raise NotFound()

        matching_routes = \
            [m for m in matching_paths if m.method == request.method]
        if not matching_routes:
            valid_methods = sorted(m.method for m in matching_paths)
            raise MethodNotAllowed(valid_methods)

        assert len(matching_routes) == 1
        route = matching_routes[0]
        return route.handler, route.path_args

    def _call_handler(handler: RouteHandler, path_args: Sequence[Any]) \
            -> Iterable[bytes]:
        try:
            return handler(request, path_args, start_response)
        except ArgumentsError as exc:
            return _respond_arguments_error(start_response, exc.arguments)
        except HTTPException as exc:
            return _respond_http_exception(start_response, exc)

    return find_route_and_call_handler()


class _RouteArguments:

    def __init__(self, request: Request,
                 template_handlers: _TemplateHandlerDict) -> None:
        self._request = request
        self._handlers = template_handlers
        self._cache = {}  # type: Dict[Tuple[str, str], Any]

    def parse_argument(self, paths: Sequence[Any], name: str, path: str) \
            -> Any:
        key = name, path
        if key not in self._cache:
            handler = self._handlers[name]
            self._cache[key] = handler(self._request, paths, path)
        return self._cache[key]


class _RouteMatcher:

    def __init__(self, handler: _RouteHandler, path: str,
                 arguments: _RouteArguments) -> None:
        self._handler = handler
        self.method = handler.method
        self.handler = handler.handler
        self._path = _split_path(path[1:])
        self._arguments = arguments
        self.path_args = []  # type: List[Any]
        if self._do_path_and_tmpl_differ_in_length():
            self.matches = False
        else:
            self.matches = self._match_parts()

    def _do_path_and_tmpl_differ_in_length(self) -> bool:
        if self._handler.wildcard:
            return len(self._handler.path) > len(self._path)
        else:
            return len(self._handler.path) != len(self._path)

    def _match_parts(self) -> bool:
        for tmpl_part, path_part in self._path_compare_iter():
            tmpl_type, text = tmpl_part
            if tmpl_type == _TemplatePartType.STATIC:
                if text != path_part:
                    return False
            elif tmpl_type == _TemplatePartType.PATTERN:
                try:
                    arg = self._arguments.parse_argument(
                        self.path_args, text, path_part)
                except ValueError:
                    return False
                self.path_args.append(arg)
            else:
                raise AssertionError("unhandled template type")
        if self._handler.wildcard:
            remaining_path = [""] + self._path[len(self._handler.path):]
            self.path_args.append("/".join(remaining_path))
        return True

    def _path_compare_iter(self) -> Iterator[Tuple[_RouteTemplatePart, str]]:
        return zip(self._handler.path, self._path)


def _respond_not_found(request: Request, start_response: StartResponse) \
        -> Iterable[bytes]:
    path = cast(str, request.environ.get("PATH_INFO", ""))
    message = "Path '{}' not found.".format(path)
    page = http_status_page(HTTPStatus.NOT_FOUND, message=message)
    return respond_with_html(
        start_response, page, status=HTTPStatus.NOT_FOUND)


def _respond_method_not_allowed(
        start_response: StartResponse,
        method: str, allowed_methods: Sequence[str]) \
        -> Iterable[bytes]:
    method_string = " or ".join(allowed_methods)
    message = "Method '{}' not allowed. Please try {}.".format(
        method, method_string)
    html = http_status_page(HTTPStatus.METHOD_NOT_ALLOWED, message=message)
    return respond_with_html(
        start_response, html, status=HTTPStatus.METHOD_NOT_ALLOWED,
        extra_headers=[("Allow", ", ".join(allowed_methods))])


def _respond_internal_server_error(start_response: StartResponse) \
        -> Iterable[bytes]:
    html = http_status_page(HTTPStatus.INTERNAL_SERVER_ERROR,
                            message="Internal server error.")
    return respond_with_html(start_response, html,
                             status=HTTPStatus.INTERNAL_SERVER_ERROR)


def _respond_http_exception(start_response: StartResponse,
                            exception: HTTPException) -> Iterator[bytes]:
    status = HTTPStatus(exception.code)
    html = http_status_page(status, message=exception.description)
    return respond_with_html(start_response, html, status=status)


def _respond_arguments_error(start_response: StartResponse,
                             arguments: BadArgumentsDict) -> Iterator[bytes]:
    html = bad_arguments_page(arguments)
    return respond_with_html(
        start_response, html, status=HTTPStatus.BAD_REQUEST)
