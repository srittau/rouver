from rouver.exceptions import ArgumentsError


class TestArgumentsError:
    def test_message(self) -> None:
        error = ArgumentsError({"foo": "bar"})
        assert str(error) == "400 Bad Request: invalid arguments"

    def test_arguments(self) -> None:
        error = ArgumentsError({"foo": "bar"})
        assert error.arguments == {"foo": "bar"}
