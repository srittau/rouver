from typing import Any, Callable, Dict, Iterable, Mapping, Sequence, Tuple

from werkzeug.wrappers import Request

# (name, value)
Header = Tuple[str, str]

WSGIEnvironment = Dict[str, Any]

# (body) -> None
StartResponseReturnType = Callable[[bytes], None]

# (status: str, headers: List[Headers], exc_info) -> response
StartResponse = Callable[..., StartResponseReturnType]

WSGIResponse = Iterable[bytes]

WSGIApplication = Callable[[WSGIEnvironment, StartResponse], WSGIResponse]

# (method, path, callback)
RouteDescription = Tuple[str, str, WSGIApplication]

# (request, previous_args, path_part) -> result
RouteTemplateHandler = Callable[[Request, Sequence[Any], str], Any]

BadArgumentsDict = Mapping[str, str]
