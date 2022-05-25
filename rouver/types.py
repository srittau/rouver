from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Mapping, Tuple

from typing_extensions import TypeAlias
from werkzeug.wrappers import Request

# (name, value)
Header: TypeAlias = Tuple[str, str]

WSGIEnvironment: TypeAlias = Dict[str, Any]

# (body) -> None
StartResponseReturnType: TypeAlias = Callable[[bytes], object]

# (status: str, headers: List[Headers], exc_info) -> response
StartResponse: TypeAlias = Callable[..., StartResponseReturnType]

WSGIResponse: TypeAlias = Iterable[bytes]

WSGIApplication: TypeAlias = Callable[
    [WSGIEnvironment, StartResponse], WSGIResponse
]

# (method, path, callback)
RouteDescription: TypeAlias = Tuple[str, str, WSGIApplication]

# (request, previous_args, path_part) -> result
RouteTemplateHandler: TypeAlias = Callable[
    [Request, Tuple[Any, ...], str], Any
]

BadArgumentsDict: TypeAlias = Mapping[str, str]
