from unittest import TestCase

from asserts import assert_equal

from rouver.exceptions import ArgumentsError


class ArgumentsErrorTest(TestCase):

    def test_message(self) -> None:
        error = ArgumentsError({"foo": "bar"})
        assert_equal("400 Bad Request: invalid arguments", str(error))

    def test_arguments(self) -> None:
        error = ArgumentsError({"foo": "bar"})
        assert_equal({"foo": "bar"}, error.arguments)
