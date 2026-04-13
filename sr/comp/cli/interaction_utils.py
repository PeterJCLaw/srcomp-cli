import abc
import contextlib
import io
import textwrap
from collections.abc import Iterator, Sequence
from typing import Generic, TypeVar

T = TypeVar('T')


BOLD = '\033[1m'
FAIL = '\033[91m'
OKBLUE = '\033[94m'
ENDC = '\033[0m'


class FatalCommandError(RuntimeError):
    """
    Something went wrong which means that the command cannot continue.

    This a marker exception and callsites should handle their own displaying of
    a suitable error message. The message passed to this exception will not be
    shown to the user and is intended for logging.
    """

    def __init__(self, log_message: str, exit_code: int = 1) -> None:
        super().__init__(log_message, exit_code)
        self.log_message = log_message
        self.exit_code = exit_code


class UserInteractions(Generic[T], abc.ABC):
    @abc.abstractmethod
    def format_buffer(self, buffer: io.StringIO) -> T:
        raise NotImplementedError(f"{type(self).__name__}.format_buffer")

    @abc.abstractmethod
    def format_info(self, message: str) -> T:
        raise NotImplementedError(f"{type(self).__name__}.format_info")

    @abc.abstractmethod
    def format_strong(self, message: str) -> T:
        raise NotImplementedError(f"{type(self).__name__}.format_strong")

    @abc.abstractmethod
    def format_strong_ok(self, message: str) -> T:
        raise NotImplementedError(f"{type(self).__name__}.format_strong_ok")

    @abc.abstractmethod
    def format_error(self, message: str) -> T:
        raise NotImplementedError(f"{type(self).__name__}.format_error")

    @abc.abstractmethod
    def message(self, message: T) -> None:
        raise NotImplementedError(f"{type(self).__name__}.message")

    @abc.abstractmethod
    def get_input(self, message: T) -> str:
        raise NotImplementedError(f"{type(self).__name__}.get_input")

    def show_buffer(self, buffer: io.StringIO) -> None:
        self.message(self.format_buffer(buffer))

    def show_info(self, message: str) -> None:
        self.message(self.format_info(message))

    def show_strong(self, message: str) -> None:
        self.message(self.format_strong(message))

    def show_strong_ok(self, message: str) -> None:
        self.message(self.format_strong_ok(message))

    def show_error(self, message: str) -> None:
        self.message(self.format_error(message))

    def query(
        self,
        question: str,
        options: Sequence[str],
        default: str | None = None,
    ) -> str:
        if default and default not in options:
            raise ValueError(
                f"Default value {default!r} not an available option (options: {options!r})",
            )

        options = [o.upper() if o == default else o.lower() for o in options]
        assert len(set(options)) == len(options)
        opts = '/'.join(options)

        query = self.format_error(f"{question.rstrip()} [{opts}]: ")

        while True:
            # Loop until we get a suitable response from the user
            resp = self.get_input(query).lower()

            if resp in options:
                return resp

            # If there's a default value, use that
            if default:
                return default

    def query_bool(self, question: str, default: bool | None = None) -> bool:
        options = ('y', 'n')
        if default is True:
            default_str: str | None = 'y'
        elif default is False:
            default_str = 'n'
        else:
            default_str = None
        return self.query(question, options, default_str) == 'y'

    @contextlib.contextmanager
    def make_fatal(
        self,
        msg: str = '{0}',
        kind: type[Exception] = Exception,
    ) -> Iterator[None]:
        try:
            yield
        except kind as e:
            msg = msg.format(e)
            self.show_error(msg)
            raise FatalCommandError(msg, exit_code=1) from e


class CLIInteractions(UserInteractions[str]):
    def format_buffer(self, buffer: io.StringIO) -> str:
        content = buffer.getvalue().rstrip()
        if content:
            content = textwrap.indent(content, '> ')
        return content

    def format_info(self, message: str) -> str:
        return message

    def format_strong(self, message: str) -> str:
        return BOLD + message + ENDC

    def format_strong_ok(self, message: str) -> str:
        return BOLD + OKBLUE + message + ENDC

    def format_error(self, message: str) -> str:
        return BOLD + FAIL + message + ENDC

    def message(self, message: str) -> None:
        print(message)

    def get_input(self, message: str) -> str:
        return input(message)
