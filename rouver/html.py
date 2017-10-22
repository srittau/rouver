from http import HTTPStatus


def http_status_page(status: HTTPStatus, message: str) -> str:
    return """<!DOCTYPE html>
<html>
    <head>
        <title>{0.value} &mdash; {0.phrase}</title>
    </head>
    <body>
        <h1>{0.value} &mdash; {0.phrase}</h1>
        <p>{1}</p>
    </body>
</html>
""".format(status, message)


def created_at_page(url: str) -> str:
    message = 'Created at <a href="{0}">{0}</a>.'.format(url)
    return http_status_page(HTTPStatus.CREATED, message)


def see_other_page(url: str) -> str:
    message = 'Please see <a href="{0}">{0}</a>.'.format(url)
    return http_status_page(HTTPStatus.SEE_OTHER, message)
