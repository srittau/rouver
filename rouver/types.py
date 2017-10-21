from typing import Callable, Tuple, List, Dict, Any

# (name, value)
HeaderType = Tuple[str, str]

EnvironmentType = Dict[str, Any]

# (body) -> None
StartResponseReturnType = Callable[[bytes], None]

# (status, headers) -> write
StartResponseType = Callable[[str, List[HeaderType]], StartResponseReturnType]
