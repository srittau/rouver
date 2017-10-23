from http import HTTPStatus


def http_status_page(status: HTTPStatus, *,
                     message: str = "", content: str = "") -> str:
    """Create an HTML error page for a given status code.

    WARNING: The arguments "message" and "content" are not safe! Their content
    will be pasted into the page as is. Do not use with unsanitized data!
    """
    paragraph = "\n        <p>{}</p>".format(message) if message else ""
    content = content + "\n" if content else ""
    return """<!DOCTYPE html>
<html>
    <head>
        <title>{0.value} &mdash; {0.phrase}</title>
    </head>
    <body>
        <h1>{0.value} &mdash; {0.phrase}</h1>{1}
{2}    </body>
</html>
""".format(status, paragraph, content)


def created_at_page(url: str) -> str:
    message = 'Created at <a href="{0}">{0}</a>.'.format(url)
    return http_status_page(HTTPStatus.CREATED, message=message)


def see_other_page(url: str) -> str:
    message = 'Please see <a href="{0}">{0}</a>.'.format(url)
    return http_status_page(HTTPStatus.SEE_OTHER, message=message)
