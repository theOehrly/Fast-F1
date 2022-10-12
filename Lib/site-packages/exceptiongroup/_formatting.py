# traceback_exception_init() adapted from trio
#
# _ExceptionPrintContext and traceback_exception_format() copied from the standard
# library
from __future__ import annotations

import collections.abc
import sys
import textwrap
import traceback
from functools import singledispatch
from types import TracebackType
from typing import Any, List, Optional

from ._exceptions import BaseExceptionGroup

max_group_width = 15
max_group_depth = 10
_cause_message = (
    "\nThe above exception was the direct cause of the following exception:\n\n"
)

_context_message = (
    "\nDuring handling of the above exception, another exception occurred:\n\n"
)


def _format_final_exc_line(etype, value):
    valuestr = _safe_string(value, "exception")
    if value is None or not valuestr:
        line = f"{etype}\n"
    else:
        line = f"{etype}: {valuestr}\n"

    return line


def _safe_string(value, what, func=str):
    try:
        return func(value)
    except BaseException:
        return f"<{what} {func.__name__}() failed>"


class _ExceptionPrintContext:
    def __init__(self):
        self.seen = set()
        self.exception_group_depth = 0
        self.need_close = False

    def indent(self):
        return " " * (2 * self.exception_group_depth)

    def emit(self, text_gen, margin_char=None):
        if margin_char is None:
            margin_char = "|"
        indent_str = self.indent()
        if self.exception_group_depth:
            indent_str += margin_char + " "

        if isinstance(text_gen, str):
            yield textwrap.indent(text_gen, indent_str, lambda line: True)
        else:
            for text in text_gen:
                yield textwrap.indent(text, indent_str, lambda line: True)


def exceptiongroup_excepthook(
    etype: type[BaseException], value: BaseException, tb: TracebackType | None
) -> None:
    sys.stderr.write("".join(traceback.format_exception(etype, value, tb)))


class PatchedTracebackException(traceback.TracebackException):
    def __init__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType,
        *,
        limit: int | None = None,
        lookup_lines: bool = True,
        capture_locals: bool = False,
        compact: bool = False,
        _seen: set[int] | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {}
        if sys.version_info >= (3, 10):
            kwargs["compact"] = compact

        # Capture the original exception and its cause and context as
        # TracebackExceptions
        traceback_exception_original_init(
            self,
            exc_type,
            exc_value,
            exc_traceback,
            limit=limit,
            lookup_lines=lookup_lines,
            capture_locals=capture_locals,
            _seen=_seen,
            **kwargs,
        )

        seen_was_none = _seen is None

        if _seen is None:
            _seen = set()

        # Capture each of the exceptions in the ExceptionGroup along with each of
        # their causes and contexts
        if isinstance(exc_value, BaseExceptionGroup):
            embedded = []
            for exc in exc_value.exceptions:
                if id(exc) not in _seen:
                    embedded.append(
                        PatchedTracebackException(
                            type(exc),
                            exc,
                            exc.__traceback__,
                            lookup_lines=lookup_lines,
                            capture_locals=capture_locals,
                            # copy the set of _seen exceptions so that duplicates
                            # shared between sub-exceptions are not omitted
                            _seen=None if seen_was_none else set(_seen),
                        )
                    )
            self.exceptions = embedded
            self.msg = exc_value.message
        else:
            self.exceptions = None
        self.__notes__ = getattr(exc_value, "__notes__", ())

    def format(self, *, chain=True, _ctx=None):
        if _ctx is None:
            _ctx = _ExceptionPrintContext()

        output = []
        exc = self
        if chain:
            while exc:
                if exc.__cause__ is not None:
                    chained_msg = _cause_message
                    chained_exc = exc.__cause__
                elif exc.__context__ is not None and not exc.__suppress_context__:
                    chained_msg = _context_message
                    chained_exc = exc.__context__
                else:
                    chained_msg = None
                    chained_exc = None

                output.append((chained_msg, exc))
                exc = chained_exc
        else:
            output.append((None, exc))

        for msg, exc in reversed(output):
            if msg is not None:
                yield from _ctx.emit(msg)
            if exc.exceptions is None:
                if exc.stack:
                    yield from _ctx.emit("Traceback (most recent call last):\n")
                    yield from _ctx.emit(exc.stack.format())
                yield from _ctx.emit(exc.format_exception_only())
            elif _ctx.exception_group_depth > max_group_depth:
                # exception group, but depth exceeds limit
                yield from _ctx.emit(f"... (max_group_depth is {max_group_depth})\n")
            else:
                # format exception group
                is_toplevel = _ctx.exception_group_depth == 0
                if is_toplevel:
                    _ctx.exception_group_depth += 1

                if exc.stack:
                    yield from _ctx.emit(
                        "Exception Group Traceback (most recent call last):\n",
                        margin_char="+" if is_toplevel else None,
                    )
                    yield from _ctx.emit(exc.stack.format())

                yield from _ctx.emit(exc.format_exception_only())
                num_excs = len(exc.exceptions)
                if num_excs <= max_group_width:
                    n = num_excs
                else:
                    n = max_group_width + 1
                _ctx.need_close = False
                for i in range(n):
                    last_exc = i == n - 1
                    if last_exc:
                        # The closing frame may be added by a recursive call
                        _ctx.need_close = True

                    if max_group_width is not None:
                        truncated = i >= max_group_width
                    else:
                        truncated = False
                    title = f"{i + 1}" if not truncated else "..."
                    yield (
                        _ctx.indent()
                        + ("+-" if i == 0 else "  ")
                        + f"+---------------- {title} ----------------\n"
                    )
                    _ctx.exception_group_depth += 1
                    if not truncated:
                        yield from exc.exceptions[i].format(chain=chain, _ctx=_ctx)
                    else:
                        remaining = num_excs - max_group_width
                        plural = "s" if remaining > 1 else ""
                        yield from _ctx.emit(
                            f"and {remaining} more exception{plural}\n"
                        )

                    if last_exc and _ctx.need_close:
                        yield _ctx.indent() + "+------------------------------------\n"
                        _ctx.need_close = False
                    _ctx.exception_group_depth -= 1

                if is_toplevel:
                    assert _ctx.exception_group_depth == 1
                    _ctx.exception_group_depth = 0

    def format_exception_only(self):
        """Format the exception part of the traceback.
        The return value is a generator of strings, each ending in a newline.
        Normally, the generator emits a single string; however, for
        SyntaxError exceptions, it emits several lines that (when
        printed) display detailed information about where the syntax
        error occurred.
        The message indicating which exception occurred is always the last
        string in the output.
        """
        if self.exc_type is None:
            yield traceback._format_final_exc_line(None, self._str)
            return

        stype = self.exc_type.__qualname__
        smod = self.exc_type.__module__
        if smod not in ("__main__", "builtins"):
            if not isinstance(smod, str):
                smod = "<unknown>"
            stype = smod + "." + stype

        if not issubclass(self.exc_type, SyntaxError):
            yield _format_final_exc_line(stype, self._str)
        elif traceback_exception_format_syntax_error is not None:
            yield from traceback_exception_format_syntax_error(self, stype)
        else:
            yield from traceback_exception_original_format_exception_only(self)

        if isinstance(self.__notes__, collections.abc.Sequence):
            for note in self.__notes__:
                note = _safe_string(note, "note")
                yield from [line + "\n" for line in note.split("\n")]
        elif self.__notes__ is not None:
            yield _safe_string(self.__notes__, "__notes__", func=repr)


traceback_exception_original_init = traceback.TracebackException.__init__
traceback_exception_original_format = traceback.TracebackException.format
traceback_exception_original_format_exception_only = (
    traceback.TracebackException.format_exception_only
)
traceback_exception_format_syntax_error = getattr(
    traceback.TracebackException, "_format_syntax_error", None
)
if sys.excepthook is sys.__excepthook__:
    traceback.TracebackException.__init__ = (  # type: ignore[assignment]
        PatchedTracebackException.__init__
    )
    traceback.TracebackException.format = (  # type: ignore[assignment]
        PatchedTracebackException.format
    )
    traceback.TracebackException.format_exception_only = (  # type: ignore[assignment]
        PatchedTracebackException.format_exception_only
    )
    sys.excepthook = exceptiongroup_excepthook


@singledispatch
def format_exception_only(__exc: BaseException) -> List[str]:
    return list(
        PatchedTracebackException(type(__exc), __exc, None).format_exception_only()
    )


@format_exception_only.register
def _(__exc: type, value: BaseException) -> List[str]:
    return format_exception_only(value)


@singledispatch
def format_exception(
    __exc: BaseException,
    limit: Optional[int] = None,
    chain: bool = True,
) -> List[str]:
    return list(
        PatchedTracebackException(
            type(__exc), __exc, __exc.__traceback__, limit=limit
        ).format(chain=chain)
    )


@format_exception.register
def _(
    __exc: type,
    value: BaseException,
    tb: TracebackType,
    limit: Optional[int] = None,
    chain: bool = True,
) -> List[str]:
    return format_exception(value, limit, chain)


@singledispatch
def print_exception(
    __exc: BaseException,
    limit: Optional[int] = None,
    file: Any = None,
    chain: bool = True,
) -> None:
    if file is None:
        file = sys.stderr

    for line in PatchedTracebackException(
        type(__exc), __exc, __exc.__traceback__, limit=limit
    ).format(chain=chain):
        print(line, file=file, end="")


@print_exception.register
def _(
    __exc: type,
    value: BaseException,
    tb: TracebackType,
    limit: Optional[int] = None,
    file: Any = None,
    chain: bool = True,
) -> None:
    print_exception(value, limit, file, chain)


def print_exc(
    limit: Optional[int] = None,
    file: Any | None = None,
    chain: bool = True,
) -> None:
    value = sys.exc_info()[1]
    print_exception(value, limit, file, chain)
