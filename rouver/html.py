from http import HTTPStatus

from rouver.types import BadArgumentsDict


def http_status_page(status: HTTPStatus, *,
                     html_message: str = "", html_content: str = "") -> str:
    """Create an HTML error page for a given status code.

    WARNING: The arguments "html_message" and "html_content" are not safe!
    Their content will be pasted into the page as is. Do not use with
    unsanitized data!
    """
    paragraph = \
        "\n        <p>{}</p>".format(html_message) if html_message else ""
    content = html_content + "\n" if html_content else ""
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
    return http_status_page(HTTPStatus.CREATED, html_message=message)


def temporary_redirect_page(url: str) -> str:
    message = 'Please see <a href="{0}">{0}</a>.'.format(url)
    return http_status_page(
        HTTPStatus.TEMPORARY_REDIRECT, html_message=message)


def see_other_page(url: str) -> str:
    message = 'Please see <a href="{0}">{0}</a>.'.format(url)
    return http_status_page(HTTPStatus.SEE_OTHER, html_message=message)


def bad_arguments_page(arguments: BadArgumentsDict) -> str:
    content = bad_arguments_list(arguments)
    return http_status_page(
        HTTPStatus.BAD_REQUEST, html_message="Invalid arguments:",
        html_content=content)


def bad_arguments_list(arguments: BadArgumentsDict) -> str:
    if not arguments:
        return ""

    def format_item(name: str, error: str) -> str:
        return """    <li class="argument">
        <span class="argument-name">{name}</span>:
        <span class="error-message">{error}</span>
    </li>
""".format(name=name, error=error)

    items = [format_item(k, arguments[k]) for k in sorted(arguments)]

    return '<ul class="bad-arguments">\n{}</ul>\n'.format("".join(items))
