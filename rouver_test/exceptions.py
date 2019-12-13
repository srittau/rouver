from asserts import assert_equal
from dectest import TestCase, test

from rouver.exceptions import ArgumentsError


class ArgumentsErrorTest(TestCase):
    @test
    def message(self) -> None:
        error = ArgumentsError({"foo": "bar"})
        assert_equal("400 Bad Request: invalid arguments", str(error))

    @test
    def arguments(self) -> None:
        error = ArgumentsError({"foo": "bar"})
        assert_equal({"foo": "bar"}, error.arguments)
