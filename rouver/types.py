from typing import Callable, Tuple, Dict, Any, Iterable, Sequence, Mapping

from werkzeug.wrappers import Request

# (name, value)
Header = Tuple[str, str]

WSGIEnvironment = Dict[str, Any]

# (body) -> None
StartResponseReturnType = Callable[[bytes], None]

# (status, headers) -> response
StartResponse = Callable[[str, Sequence[Header]], StartResponseReturnType]

WSGIResponse = Iterable[bytes]

WSGIApplication = Callable[[WSGIEnvironment, StartResponse], WSGIResponse]

# (request, path, start_response) -> response
RouteHandler = \
    Callable[[Request, Sequence[Any], StartResponse], Iterable[bytes]]

# (method, path, callback)
RouteDescription = Tuple[str, str, RouteHandler]

# (request, previous_args, path_part) -> result
RouteTemplateHandler = Callable[[Request, Sequence[Any], str], Any]

BadArgumentsDict = Mapping[str, str]
