from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

from werkzeug.wrappers import Request

if TYPE_CHECKING:
    from _typeshed import OptExcInfo

# (name, value)
Header: TypeAlias = tuple[str, str]

WSGIEnvironment: TypeAlias = dict[str, Any]

# (body) -> None
StartResponseReturnType: TypeAlias = Callable[[bytes], object]


class StartResponse(Protocol):
    def __call__(
        self,
        status: str,
        headers: list[tuple[str, str]],
        exc_info: OptExcInfo | None = ...,
        /,
    ) -> StartResponseReturnType: ...


WSGIResponse: TypeAlias = Iterable[bytes]

WSGIApplication: TypeAlias = Callable[
    [WSGIEnvironment, StartResponse], WSGIResponse
]

# (method, path, callback)
RouteDescription: TypeAlias = tuple[str, str, WSGIApplication]

# (request, previous_args, path_part) -> result
RouteTemplateHandler: TypeAlias = Callable[
    [Request, tuple[Any, ...], str], Any
]

BadArgumentsDict: TypeAlias = Mapping[str, str]
