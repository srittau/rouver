from io import BytesIO, StringIO

from rouver.types import EnvironmentType


def default_environment() -> EnvironmentType:
    return {
        "REQUEST_METHOD": "GET",
        "SERVER_NAME": "www.example.com",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(b""),
        "wsgi.errors": StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
