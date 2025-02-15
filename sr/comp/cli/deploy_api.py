import abc
import io
import textwrap
from collections.abc import Sequence
from typing import Generic, TypeVar

T = TypeVar('T')


BOLD = '\033[1m'
FAIL = '\033[91m'
OKBLUE = '\033[94m'
ENDC = '\033[0m'


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
        if default:
            assert default in options

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

    def query_bool(self, question: str, default_val: bool | None = None) -> bool:
        options = ('y', 'n')
        if default_val is True:
            default: str | None = 'y'
        elif default_val is False:
            default = 'n'
        else:
            default = None
        return self.query(question, options, default) == 'y'


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
