import re
from urllib.parse import quote, urljoin

from werkzeug import Request

_url_scheme_re = re.compile(r"^[a-zA-Z][a-zA-Z0-9.+-]*:")


def absolute_url(request: Request, path: str) -> str:
    """
    Construct an absolute URL, using the request URL as base.

    Non-printable and non-ASCII characters in the path are encoded,
    but other characters, most notably slashes and percent signs are
    not encoded. Make sure to call urllib.parse.quote() on paths that
    can potentially contain such characters before passing them to
    absolute_url().
    """
    base_url: str = request.base_url
    return urljoin(base_url, quote(path, safe="/:?&$@,;+=%~"))
