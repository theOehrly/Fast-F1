from __future__ import annotations

from collections.abc import Sequence
from functools import partial
from inspect import getmro, isclass
from typing import Any, Callable, Generic, Tuple, Type, TypeVar, Union, cast

T = TypeVar("T", bound="BaseExceptionGroup")
EBase = TypeVar("EBase", bound=BaseException)
E = TypeVar("E", bound=Exception)
_SplitCondition = Union[
    Type[EBase],
    Tuple[Type[EBase], ...],
    Callable[[EBase], bool],
]


def check_direct_subclass(
    exc: BaseException, parents: tuple[type[BaseException]]
) -> bool:
    for cls in getmro(exc.__class__)[:-1]:
        if cls in parents:
            return True

    return False


def get_condition_filter(condition: _SplitCondition) -> Callable[[BaseException], bool]:
    if isclass(condition) and issubclass(
        cast(Type[BaseException], condition), BaseException
    ):
        return partial(check_direct_subclass, parents=(condition,))
    elif isinstance(condition, tuple):
        if all(isclass(x) and issubclass(x, BaseException) for x in condition):
            return partial(check_direct_subclass, parents=condition)
    elif callable(condition):
        return cast(Callable[[BaseException], bool], condition)

    raise TypeError("expected a function, exception type or tuple of exception types")


class BaseExceptionGroup(BaseException, Generic[EBase]):
    """A combination of multiple unrelated exceptions."""

    def __new__(
        cls, __message: str, __exceptions: Sequence[EBase]
    ) -> BaseExceptionGroup[EBase] | ExceptionGroup[E]:
        if not isinstance(__message, str):
            raise TypeError(f"argument 1 must be str, not {type(__message)}")
        if not isinstance(__exceptions, Sequence):
            raise TypeError("second argument (exceptions) must be a sequence")
        if not __exceptions:
            raise ValueError(
                "second argument (exceptions) must be a non-empty sequence"
            )

        for i, exc in enumerate(__exceptions):
            if not isinstance(exc, BaseException):
                raise ValueError(
                    f"Item {i} of second argument (exceptions) is not an " f"exception"
                )

        if cls is BaseExceptionGroup:
            if all(isinstance(exc, Exception) for exc in __exceptions):
                cls = ExceptionGroup

        return super().__new__(cls, __message, __exceptions)

    def __init__(self, __message: str, __exceptions: Sequence[EBase], *args: Any):
        super().__init__(__message, __exceptions, *args)
        self._message = __message
        self._exceptions = __exceptions

    def add_note(self, note: str):
        if not isinstance(note, str):
            raise TypeError(
                f"Expected a string, got note={note!r} (type {type(note).__name__})"
            )
        if not hasattr(self, "__notes__"):
            self.__notes__ = []
        self.__notes__.append(note)

    @property
    def message(self) -> str:
        return self._message

    @property
    def exceptions(self) -> tuple[EBase, ...]:
        return tuple(self._exceptions)

    def subgroup(self: T, __condition: _SplitCondition[EBase]) -> T | None:
        condition = get_condition_filter(__condition)
        modified = False
        if condition(self):
            return self

        exceptions: list[BaseException] = []
        for exc in self.exceptions:
            if isinstance(exc, BaseExceptionGroup):
                subgroup = exc.subgroup(condition)
                if subgroup is not None:
                    exceptions.append(subgroup)

                if subgroup is not exc:
                    modified = True
            elif condition(exc):
                exceptions.append(exc)
            else:
                modified = True

        if not modified:
            return self
        elif exceptions:
            group = self.derive(exceptions)
            group.__cause__ = self.__cause__
            group.__context__ = self.__context__
            group.__traceback__ = self.__traceback__
            return group
        else:
            return None

    def split(
        self: T, __condition: _SplitCondition[EBase]
    ) -> tuple[T | None, T | None]:
        condition = get_condition_filter(__condition)
        if condition(self):
            return self, None

        matching_exceptions: list[BaseException] = []
        nonmatching_exceptions: list[BaseException] = []
        for exc in self.exceptions:
            if isinstance(exc, BaseExceptionGroup):
                matching, nonmatching = exc.split(condition)
                if matching is not None:
                    matching_exceptions.append(matching)

                if nonmatching is not None:
                    nonmatching_exceptions.append(nonmatching)
            elif condition(exc):
                matching_exceptions.append(exc)
            else:
                nonmatching_exceptions.append(exc)

        matching_group: T | None = None
        if matching_exceptions:
            matching_group = self.derive(matching_exceptions)
            matching_group.__cause__ = self.__cause__
            matching_group.__context__ = self.__context__
            matching_group.__traceback__ = self.__traceback__

        nonmatching_group: T | None = None
        if nonmatching_exceptions:
            nonmatching_group = self.derive(nonmatching_exceptions)
            nonmatching_group.__cause__ = self.__cause__
            nonmatching_group.__context__ = self.__context__
            nonmatching_group.__traceback__ = self.__traceback__

        return matching_group, nonmatching_group

    def derive(self: T, __excs: Sequence[EBase]) -> T:
        eg = BaseExceptionGroup(self.message, __excs)
        if hasattr(self, "__notes__"):
            # Create a new list so that add_note() only affects one exceptiongroup
            eg.__notes__ = list(self.__notes__)
        return eg

    def __str__(self) -> str:
        suffix = "" if len(self._exceptions) == 1 else "s"
        return f"{self.message} ({len(self._exceptions)} sub-exception{suffix})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, {self._exceptions!r})"


class ExceptionGroup(BaseExceptionGroup[E], Exception, Generic[E]):
    def __new__(cls, __message: str, __exceptions: Sequence[E]) -> ExceptionGroup[E]:
        instance: ExceptionGroup[E] = super().__new__(cls, __message, __exceptions)
        if cls is ExceptionGroup:
            for exc in __exceptions:
                if not isinstance(exc, Exception):
                    raise TypeError("Cannot nest BaseExceptions in an ExceptionGroup")

        return instance
