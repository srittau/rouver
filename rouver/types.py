from types import TracebackType
from typing import \
    Callable, Tuple, Dict, Any, Iterable, Sequence, Mapping, Optional, Type, \
    Protocol, List

from werkzeug.wrappers import Request

# (name, value)
Header = Tuple[str, str]

WSGIEnvironment = Dict[str, Any]

_exc_info = Tuple[Optional[Type[BaseException]],
                  Optional[BaseException],
                  Optional[TracebackType]]

# (body) -> None
StartResponseReturnType = Callable[[bytes], None]

class StartResponse(Protocol):
    def __call__(self, status: str, headers: List[Header],
                 exc_info: Optional[_exc_info] = None) \
            -> StartResponseReturnType: ...

WSGIResponse = Iterable[bytes]

WSGIApplication = Callable[[WSGIEnvironment, StartResponse], WSGIResponse]

# (method, path, callback)
RouteDescription = Tuple[str, str, WSGIApplication]

# (request, previous_args, path_part) -> result
RouteTemplateHandler = Callable[[Request, Sequence[Any], str], Any]

BadArgumentsDict = Mapping[str, str]
