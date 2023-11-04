import operator
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, FrozenSet, Generator, Sequence, Union

import httpx
import pytest
from pytest_mock import MockerFixture

from permchain.channels.archive import UniqueArchive
from permchain.channels.base import EmptyChannelError, InvalidUpdateError
from permchain.channels.binop import BinaryOperatorAggregate
from permchain.channels.context import Context
from permchain.channels.inbox import Inbox
from permchain.channels.last_value import LastValue


def test_last_value() -> None:
    with LastValue(int).empty() as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        with pytest.raises(EmptyChannelError):
            channel.get()
        with pytest.raises(InvalidUpdateError):
            channel.update([5, 6])

        channel.update([3])
        assert channel.get() == 3
        channel.update([4])
        assert channel.get() == 4


async def test_last_value_async() -> None:
    async with LastValue(int).aempty() as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        with pytest.raises(EmptyChannelError):
            channel.get()
        with pytest.raises(InvalidUpdateError):
            channel.update([5, 6])

        channel.update([3])
        assert channel.get() == 3
        channel.update([4])
        assert channel.get() == 4


def test_inbox() -> None:
    with Inbox(str).empty() as channel:
        assert channel.ValueType is Sequence[str]
        assert channel.UpdateType is Union[str, Sequence[str]]

        with pytest.raises(EmptyChannelError):
            channel.get()

        channel.update(["a", "b"])
        assert channel.get() == ("a", "b")
        channel.update([["c"], "d"])
        assert channel.get() == ("c", "d")


async def test_inbox_async() -> None:
    async with Inbox(str).aempty() as channel:
        assert channel.ValueType is Sequence[str]
        assert channel.UpdateType is Union[str, Sequence[str]]

        with pytest.raises(EmptyChannelError):
            channel.get()

        channel.update(["a", "b"])
        assert channel.get() == ("a", "b")
        channel.update(["c"])
        channel.update([["c"], "d"])
        assert channel.get() == ("c", "d")


def test_set() -> None:
    with UniqueArchive(str).empty() as channel:
        assert channel.ValueType is FrozenSet[str]
        assert channel.UpdateType is str

        assert channel.get() == frozenset()
        channel.update(["a", "b"])
        assert channel.get() == frozenset(("a", "b"))
        channel.update(["b", "c"])
        assert channel.get() == frozenset(("a", "b", "c"))


async def test_set_async() -> None:
    async with UniqueArchive(str).aempty() as channel:
        assert channel.ValueType is FrozenSet[str]
        assert channel.UpdateType is str

        assert channel.get() == frozenset()
        channel.update(["a", "b"])
        assert channel.get() == frozenset(("a", "b"))
        channel.update(["b", "c"])
        assert channel.get() == frozenset(("a", "b", "c"))


def test_binop() -> None:
    with BinaryOperatorAggregate(int, operator.add).empty() as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        with pytest.raises(EmptyChannelError):
            channel.get()

        channel.update([1, 2, 3])
        assert channel.get() == 6
        channel.update([4])
        assert channel.get() == 10


async def test_binop_async() -> None:
    async with BinaryOperatorAggregate(int, operator.add).aempty() as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        with pytest.raises(EmptyChannelError):
            channel.get()

        channel.update([1, 2, 3])
        assert channel.get() == 6
        channel.update([4])
        assert channel.get() == 10


def test_ctx_manager(mocker: MockerFixture) -> None:
    setup = mocker.Mock()
    cleanup = mocker.Mock()

    @contextmanager
    def an_int() -> Generator[int, None, None]:
        setup()
        try:
            yield 5
        finally:
            cleanup()

    with Context(an_int, None, int).empty() as channel:
        assert setup.call_count == 1
        assert cleanup.call_count == 0

        assert channel.ValueType is int
        with pytest.raises(InvalidUpdateError):
            assert channel.UpdateType is None

        assert channel.get() == 5

        with pytest.raises(InvalidUpdateError):
            channel.update([5])  # type: ignore

    assert setup.call_count == 1
    assert cleanup.call_count == 1


def test_ctx_manager_ctx(mocker: MockerFixture) -> None:
    with Context(httpx.Client).empty() as channel:
        assert channel.ValueType is httpx.Client
        with pytest.raises(InvalidUpdateError):
            assert channel.UpdateType is None

        assert isinstance(channel.get(), httpx.Client)

        with pytest.raises(InvalidUpdateError):
            channel.update([5])  # type: ignore


async def test_ctx_manager_async(mocker: MockerFixture) -> None:
    setup = mocker.Mock()
    cleanup = mocker.Mock()

    @contextmanager
    def an_int_sync() -> Generator[int, None, None]:
        try:
            yield 5
        finally:
            pass

    @asynccontextmanager
    async def an_int() -> AsyncGenerator[int, None]:
        setup()
        try:
            yield 5
        finally:
            cleanup()

    async with Context(an_int_sync, an_int, int).aempty() as channel:
        assert setup.call_count == 1
        assert cleanup.call_count == 0

        assert channel.ValueType is int
        with pytest.raises(InvalidUpdateError):
            assert channel.UpdateType is None

        assert channel.get() == 5

        with pytest.raises(InvalidUpdateError):
            channel.update([5])  # type: ignore

    assert setup.call_count == 1
    assert cleanup.call_count == 1