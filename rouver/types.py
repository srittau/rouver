from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeAlias

from werkzeug.wrappers import Request

# (name, value)
Header: TypeAlias = tuple[str, str]

WSGIEnvironment: TypeAlias = dict[str, Any]

# (body) -> None
StartResponseReturnType: TypeAlias = Callable[[bytes], object]

# (status: str, headers: List[Headers], exc_info) -> response
StartResponse: TypeAlias = Callable[..., StartResponseReturnType]

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
