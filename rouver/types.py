from typing import Callable, Tuple, List, Dict, Any, Iterable

from werkzeug.wrappers import Request

# (name, value)
HeaderType = Tuple[str, str]

EnvironmentType = Dict[str, Any]

# (body) -> None
StartResponseReturnType = Callable[[bytes], None]

# (status, headers) -> write
StartResponseType = Callable[[str, List[HeaderType]], StartResponseReturnType]

# (request, path, start_response) -> response
RouteHandler = \
    Callable[[Request, List[Any], StartResponseType], Iterable[bytes]]

# (method, path, callback)
RouteType = Tuple[str, str, RouteHandler]

# (request, previous_args, path_part) -> result
RouteTemplateHandler = Callable[[Request, List[Any], str], Any]
