from werkzeug import Request

from rouver.util import absolute_url


class TestAbsoluteURL:
    @staticmethod
    def _create_request(*, path_info: str = "/path") -> Request:
        return Request(
            {
                "wsgi.url_scheme": "https",
                "SERVER_NAME": "example.com",
                "SERVER_PORT": "443",
                "SCRIPT_NAME": "/base/",
                "PATH_INFO": path_info,
            }
        )

    def test_path_is_not_ascii(self) -> None:
        request = self._create_request()
        assert (
            absolute_url(request, "/~föo") == "https://example.com/~f%C3%B6o"
        )

    def test_path_is_absolute(self) -> None:
        request = self._create_request()
        assert (
            absolute_url(request, "https://example.org/foo")
            == "https://example.org/foo"
        )

    def test_path_is_root_relative(self) -> None:
        request = self._create_request()
        assert absolute_url(request, "/foo") == "https://example.com/foo"

    def test_path_is_relative__base_with_slash(self) -> None:
        request = self._create_request(path_info="/path/")
        assert (
            absolute_url(request, "foo") == "https://example.com/base/path/foo"
        )

    def test_path_is_relative__base_without_slash(self) -> None:
        request = self._create_request(path_info="/path")
        assert absolute_url(request, "foo") == "https://example.com/base/foo"

    def test_do_not_encode_special_characters(self) -> None:
        request = self._create_request()
        assert (
            absolute_url(request, "/foo?bar=baz&abc=%6A;+,@:$")
            == "https://example.com/foo?bar=baz&abc=%6A;+,@:$"
        )
