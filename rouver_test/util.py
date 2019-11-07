from asserts import assert_equal
from dectest import TestCase, test
from werkzeug import Request

from rouver.util import absolute_url


class AbsoluteURLTest(TestCase):
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

    @test
    def path_is_not_ascii(self) -> None:
        request = self._create_request()
        url = absolute_url(request, "/~föo")
        assert_equal("https://example.com/~f%C3%B6o", url)

    @test
    def path_is_absolute(self) -> None:
        request = self._create_request()
        url = absolute_url(request, "https://example.org/foo")
        assert_equal("https://example.org/foo", url)

    @test
    def path_is_root_relative(self) -> None:
        request = self._create_request()
        url = absolute_url(request, "/foo")
        assert_equal("https://example.com/foo", url)

    @test
    def path_is_relative__base_with_slash(self) -> None:
        request = self._create_request(path_info="/path/")
        url = absolute_url(request, "foo")
        assert_equal("https://example.com/base/path/foo", url)

    @test
    def path_is_relative__base_without_slash(self) -> None:
        request = self._create_request(path_info="/path")
        url = absolute_url(request, "foo")
        assert_equal("https://example.com/base/foo", url)

    @test
    def do_not_encode_special_characters(self) -> None:
        request = self._create_request()
        url = absolute_url(request, "/foo?bar=baz&abc=%6A;+,@:$")
        assert_equal("https://example.com/foo?bar=baz&abc=%6A;+,@:$", url)
