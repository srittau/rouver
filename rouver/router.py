from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from enum import Enum
from http import HTTPStatus
from typing import Any, cast, Tuple
from urllib.parse import unquote

from werkzeug.exceptions import HTTPException, MethodNotAllowed, NotFound
from werkzeug.wrappers import Request

from rouver.exceptions import ArgumentsError
from rouver.html import bad_arguments_page, http_status_page
from rouver.response import respond_with_html
from rouver.types import (
    BadArgumentsDict,
    RouteDescription,
    RouteTemplateHandler,
    StartResponse,
    WSGIApplication,
    WSGIEnvironment,
)

LOGGER_NAME = "rouver"


class _TemplatePartType(Enum):

    STATIC = 1
    PATTERN = 2


def _split_path(s: str) -> list[str]:
    if not s:
        return []
    return s.split("/")


class Router:
    def __init__(self) -> None:
        self._handlers: list[_RouteHandler] = []
        self._sub_routers: list[_SubRouterHandler] = []
        self._template_handlers: dict[str, RouteTemplateHandler] = {}
        self.error_handling = True

    def __call__(
        self, environment: WSGIEnvironment, start_response: StartResponse
    ) -> Iterable[bytes]:
        try:
            return _dispatch(
                environment,
                start_response,
                self._handlers,
                self._sub_routers,
                self._template_handlers,
            )
        except Exception:
            if self.error_handling:
                logging.getLogger(LOGGER_NAME).exception(
                    "error while handling request"
                )
                return _respond_internal_server_error(start_response)
            else:
                raise

    def add_routes(self, routes: Sequence[RouteDescription]) -> None:
        self._handlers.extend(
            [_RouteHandler(r, self._template_handlers) for r in routes]
        )

    def add_template_handler(
        self, name: str, handler: RouteTemplateHandler
    ) -> None:
        self._template_handlers[name] = handler

    def add_sub_router(self, path: str, sub_router: WSGIApplication) -> None:
        """Handle a path using a sub-router.

        The following router will handle a route "/foo/sub":

        >>> def handle_sub(_, start_response):
        ...     start_response("200 OK", [])
        ...     return []
        >>> sub = Router()
        >>> sub.add_routes([("sub", "GET", handle_sub)])
        >>> router = Router()
        >>> router.add_sub_router("foo", sub)

        Sub routers can be Routers or any other WSGI application:

        >>> def sub_app(environ, start_response):
        ...     start_response("204 No Content", [])
        ...     return []
        >>> router = Router()
        >>> router.add_sub_router("foo", sub_app)

        Sub routers are matched after regular paths. This allows you to
        override selected paths in the super router:

        >>> def redirect(_, sr):
        ...     sr("307 Temporary Redirect",
        ...        [("Location", "https://www.example.com/")])
        ...     return []
        >>> sub = Router()
        >>> sub.add_routes([("sub", "GET", handle_sub)])
        >>> router = Router()
        >>> router.add_routes([("foo/bar", "GET", redirect)])
        >>> router.add_sub_router("foo", sub)
        """

        self._sub_routers.append(
            _SubRouterHandler(path, sub_router, self._template_handlers)
        )


_pattern_re = re.compile(r"^{(.*)}$")


def _parse_route_template_part(
    part: str, template_handlers: Mapping[str, RouteTemplateHandler]
) -> tuple[_TemplatePartType, str]:
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


def _parse_path(
    path_string: str,
    template_handlers: Mapping[str, RouteTemplateHandler],
    *,
    allow_wildcard: bool = False,
) -> tuple[list[tuple[_TemplatePartType, str]], bool]:
    parts = _split_path(path_string)
    if allow_wildcard and parts and parts[-1] == "*":
        parts = parts[:-1]
        wildcard = True
    else:
        wildcard = False
    templates = [
        _parse_route_template_part(part, template_handlers) for part in parts
    ]
    return templates, wildcard


class _RouteHandler:
    def __init__(
        self,
        route: RouteDescription,
        template_handlers: Mapping[str, RouteTemplateHandler],
    ) -> None:
        self.path, self.wildcard = _parse_path(
            route[0], template_handlers, allow_wildcard=True
        )
        self.method = route[1]
        self.handler = route[2]


class _SubRouterHandler:
    def __init__(
        self,
        path: str,
        router: WSGIApplication,
        template_handlers: Mapping[str, RouteTemplateHandler],
    ) -> None:
        self.path, _ = _parse_path(path, template_handlers)
        self.router = router


def _dispatch(
    environment: WSGIEnvironment,
    start_response: StartResponse,
    handlers: Sequence[_RouteHandler],
    sub_routers: Sequence[_SubRouterHandler],
    template_handlers: Mapping[str, RouteTemplateHandler],
) -> Iterable[bytes]:

    request = Request(environment)
    path = _split_path(request.path[1:])
    arguments = _RouteArguments(request, template_handlers)

    def find_route_and_call_handler() -> Iterable[bytes]:
        try:
            matcher = find_route()
        except NotFound:
            pass
        except MethodNotAllowed as exc:
            return _respond_method_not_allowed(
                start_response, request.method, exc.valid_methods
            )
        else:
            return call_handler(matcher)

        try:
            sub_matcher = find_sub_router()
        except NotFound:
            pass
        else:
            return call_sub_router(sub_matcher)

        return _respond_not_found(environment, start_response)

    def find_route() -> _RouteMatcher:
        matchers = [_RouteMatcher(h, path, arguments) for h in handlers]

        matching_paths = [m for m in matchers if m.matches]
        if not matching_paths:
            raise NotFound()

        matching_routes = [
            m for m in matching_paths if m.method == request.method
        ]
        if not matching_routes:
            valid_methods = sorted(set(m.method for m in matching_paths))
            raise MethodNotAllowed(valid_methods)

        assert len(matching_routes) >= 1
        # Workaround for https://github.com/python/mypy/issues/4345
        assert isinstance(matching_routes[0], _RouteMatcher)
        return matching_routes[0]

    def call_handler(matcher: _RouteMatcher) -> Iterable[bytes]:
        try:
            return matcher.call(environment, start_response)
        except ArgumentsError as exc:
            return _respond_arguments_error(start_response, exc.arguments)
        except HTTPException as exc:
            return _respond_http_exception(start_response, exc)

    def find_sub_router() -> _SubRouterMatcher:
        matchers = [
            _SubRouterMatcher(sub_r, path, arguments) for sub_r in sub_routers
        ]
        for m in matchers:
            if m.matches:
                return m
        raise NotFound()

    def call_sub_router(matcher: _SubRouterMatcher) -> Iterable[bytes]:
        new_environ = environment.copy()
        new_environ["rouver.original_path_info"] = environment["PATH_INFO"]
        new_environ["PATH_INFO"] = matcher.remaining_path.encode(
            "utf-8"
        ).decode("latin-1")
        return matcher.call(new_environ, start_response)

    return find_route_and_call_handler()


class _RouteArguments:
    def __init__(
        self,
        request: Request,
        template_handlers: Mapping[str, RouteTemplateHandler],
    ) -> None:
        self._request = request
        self._handlers = template_handlers
        self._cache: dict[tuple[str, str], Any] = {}

    def parse_argument(
        self, paths: Tuple[Any, ...], name: str, path: str
    ) -> Any:
        key = name, path
        if key not in self._cache:
            handler = self._handlers[name]
            self._cache[key] = handler(self._request, paths, path)
        return self._cache[key]


class _MatcherBase:
    def __init__(
        self,
        match_path: Sequence[tuple[_TemplatePartType, str]],
        request_path: Sequence[str],
        arguments: _RouteArguments,
        *,
        match_full_path: bool = False,
    ) -> None:
        if request_path and request_path[-1] == "":
            request_path = request_path[:-1]
            self._trailing_slash = True
        else:
            self._trailing_slash = False
        self._match_path = match_path
        self._request_path = request_path
        self._arguments = arguments
        self._match_full_path = match_full_path
        self.matches, self.path_args = self._check_and_parse()

    def _check_and_parse(self) -> tuple[bool, list[Any]]:
        if self._path_length_matches():
            return self._parse()
        else:
            return False, []

    def _path_length_matches(self) -> bool:
        if self._match_full_path:
            return len(self._match_path) == len(self._request_path)
        else:
            return len(self._match_path) <= len(self._request_path)

    def _parse(self) -> tuple[bool, list[Any]]:
        path_args: list[Any] = []
        for tmpl_part, path_part in self._path_compare_iter():
            try:
                decoded = unquote(path_part, errors="strict")
            except UnicodeDecodeError:
                return False, []
            tmpl_type, text = tmpl_part
            if tmpl_type == _TemplatePartType.STATIC:
                if text != decoded:
                    return False, []
            elif tmpl_type == _TemplatePartType.PATTERN:
                try:
                    arg = self._arguments.parse_argument(
                        tuple(path_args), text, decoded
                    )
                except ValueError:
                    return False, []
                path_args.append(arg)
            else:
                raise AssertionError("unhandled template type")
        return True, path_args

    def _path_compare_iter(
        self,
    ) -> Iterator[tuple[tuple[_TemplatePartType, str], str]]:
        return zip(self._match_path, self._request_path)

    @property
    def remaining_path(self) -> str:
        remaining_path = list(self._request_path[len(self._match_path) :])
        path = "/".join([""] + remaining_path)
        if self._trailing_slash:
            path += "/"
        return path


class _RouteMatcher(_MatcherBase):
    def __init__(
        self,
        handler: _RouteHandler,
        path: Sequence[str],
        arguments: _RouteArguments,
    ) -> None:
        super().__init__(
            handler.path, path, arguments, match_full_path=not handler.wildcard
        )
        self.method = handler.method
        self._handler = handler.handler

    def call(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> Iterable[bytes]:
        environ["rouver.path_args"] = self.path_args
        environ["rouver.wildcard_path"] = self.remaining_path
        return self._handler(environ, start_response)


class _SubRouterMatcher(_MatcherBase):
    def __init__(
        self,
        handler: _SubRouterHandler,
        path: Sequence[str],
        arguments: _RouteArguments,
    ) -> None:
        super().__init__(handler.path, path, arguments)
        self._router = handler.router

    def call(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> Iterable[bytes]:
        return self._router(environ, start_response)


def _respond_not_found(
    environment: WSGIEnvironment, start_response: StartResponse
) -> Iterable[bytes]:
    path = cast(str, environment.get("PATH_INFO", ""))
    message = "Path '{}' not found.".format(path)
    page = http_status_page(HTTPStatus.NOT_FOUND, message=message)
    return respond_with_html(start_response, page, status=HTTPStatus.NOT_FOUND)


def _respond_method_not_allowed(
    start_response: StartResponse,
    method: str,
    allowed_methods: Iterable[str] | None,
) -> Iterable[bytes]:
    method_string = " or ".join(allowed_methods or [])
    message = "Method '{}' not allowed. Please try {}.".format(
        method, method_string
    )
    html = http_status_page(HTTPStatus.METHOD_NOT_ALLOWED, message=message)
    return respond_with_html(
        start_response,
        html,
        status=HTTPStatus.METHOD_NOT_ALLOWED,
        extra_headers=[("Allow", ", ".join(allowed_methods or []))],
    )


def _respond_internal_server_error(
    start_response: StartResponse,
) -> Iterable[bytes]:
    html = http_status_page(
        HTTPStatus.INTERNAL_SERVER_ERROR, message="Internal server error."
    )
    return respond_with_html(
        start_response, html, status=HTTPStatus.INTERNAL_SERVER_ERROR
    )


def _respond_http_exception(
    start_response: StartResponse, exception: HTTPException
) -> Iterable[bytes]:
    assert exception.code is not None
    status = HTTPStatus(exception.code)
    html = http_status_page(status, message=exception.description or "")
    headers = [
        h for h in exception.get_headers() if h[0].lower() != "content-type"
    ]
    return respond_with_html(
        start_response,
        html,
        status=status,
        extra_headers=headers,
    )


def _respond_arguments_error(
    start_response: StartResponse, arguments: BadArgumentsDict
) -> Iterable[bytes]:
    html = bad_arguments_page(arguments)
    return respond_with_html(
        start_response, html, status=HTTPStatus.BAD_REQUEST
    )
