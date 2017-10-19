from http import HTTPStatus


def status_line(status: HTTPStatus) -> str:
    return "{0.value} {0.phrase}".format(status)
