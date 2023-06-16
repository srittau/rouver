from urllib.parse import quote, urljoin

from werkzeug import Request


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


def rfc5987_encode(key: str, s: str) -> str:
    """Encode a string according to RFC 5987 if necessary."""
    if is_rfc2616_token(s):
        return f"{key}={s}"
    elif s.isascii():
        return f"{key}={rfc2616_quote(s)}"
    else:
        return f"{key}*=UTF-8''{quote(s)}"


RFC2616_SEPARATORS = '()<>@,;:\\"/[]?={} \t'


def is_rfc2616_token(s: str) -> bool:
    """Return whether `s` is a token according to RFC 2616."""
    for c in s:
        if ord(c) < 32 or ord(c) > 126:
            return False
        if c in RFC2616_SEPARATORS:
            return False
    return True


def rfc2616_quote(s: str) -> str:
    """Quote a string according to RFC 2616."""
    quoted = ""
    for c in s:
        if ord(c) < 32 or ord(c) > 126:
            quoted += f"\\{c}"
        elif c == '"':
            quoted += '\\"'
        else:
            quoted += c
    return f'"{quoted}"'
