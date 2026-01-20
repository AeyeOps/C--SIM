"""
SimSet - SIMULA-style linked list classes.

Port of C++SIM SimSet/ module (Head.cc, Link.cc, Linkage.h).

These classes provide the classic SIMULA SIMSET linked list functionality:
- Linkage: Abstract base class with Suc/Pred navigation
- Link: List element that can be in one list at a time
- Head: List container managing a doubly-linked list of Links
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Iterator

T = TypeVar("T", bound="Link")


class Linkage(ABC):
    """
    Abstract base class for SimSet elements.

    Defines the navigation interface (Suc/Pred) that both
    Head and Link must implement.

    From SimSet/Linkage.h.
    """

    @abstractmethod
    def suc(self) -> Link | None:
        """Return successor element."""
        ...

    @abstractmethod
    def pred(self) -> Link | None:
        """Return predecessor element."""
        ...


class Link(Linkage):
    """
    Element that can be inserted into a Head list.

    A Link can only be in one list at a time. Inserting into
    a new list automatically removes from the current list.

    From SimSet/Link.cc.
    """

    def __init__(self) -> None:
        self._prev: Link | None = None
        self._next: Link | None = None
        self._the_list: Head | None = None

    def suc(self) -> Link | None:
        """Return next element in list, or None if last."""
        return self._next

    def pred(self) -> Link | None:
        """Return previous element in list, or None if first."""
        return self._prev

    def in_list(self) -> bool:
        """Check if this element is in a list."""
        return self._the_list is not None

    def _remove_element(self) -> None:
        """
        Internal: remove from current list without returning self.

        From Link.cc:54-75.
        """
        if self._the_list is None:
            return

        if self._prev is not None:
            self._prev._next = self._next

        if self._next is not None:
            self._next._prev = self._prev

        if self._the_list._first is self:
            self._the_list._first = self._next

        if self._the_list._last is self:
            self._the_list._last = self._prev

        self._the_list = None
        self._prev = None
        self._next = None

    def out(self) -> Link:
        """
        Remove from current list and return self.

        From Link.cc:77-81.
        """
        self._remove_element()
        return self

    def into(self, list_head: Head | None) -> None:
        """
        Insert at end of list, or remove if list is None.

        From Link.cc:83-93.
        """
        if list_head is not None:
            list_head.add_last(self)
        else:
            self.out()

    def precede(self, other: Link | Head) -> None:
        """
        Insert before another element or at start of list.

        From Link.cc:95-106, 157-161.
        """
        if isinstance(other, Head):
            other.add_first(self)
            return

        if other is None or not other.in_list():
            self.out()
        else:
            if self.in_list():
                self.out()
            other._add_before(self)

    def follow(self, other: Link | Head) -> None:
        """
        Insert after another element or at start of list.

        From Link.cc:108-119, 157-161.
        """
        if isinstance(other, Head):
            other.add_first(self)
            return

        if other is None or not other.in_list():
            self.out()
        else:
            if self.in_list():
                self.out()
            other._add_after(self)

    def _add_after(self, to_add: Link) -> None:
        """
        Internal: add element after this one.

        From Link.cc:121-137.
        """
        to_add._prev = self
        to_add._the_list = self._the_list

        if self._next is None:
            self._next = to_add
        else:
            self._next._prev = to_add
            to_add._next = self._next
            self._next = to_add

        if self._the_list is not None and self._the_list._last is self:
            self._the_list._last = to_add

    def _add_before(self, to_add: Link) -> None:
        """
        Internal: add element before this one.

        From Link.cc:139-155.
        """
        to_add._the_list = self._the_list
        to_add._next = self

        if self._prev is None:
            self._prev = to_add
        else:
            self._prev._next = to_add
            to_add._prev = self._prev
            self._prev = to_add

        if self._the_list is not None and self._the_list._first is self:
            self._the_list._first = to_add


class Head(Linkage):
    """
    Doubly-linked list container for Link elements.

    From SimSet/Head.cc.
    """

    def __init__(self) -> None:
        self._first: Link | None = None
        self._last: Link | None = None

    def suc(self) -> Link | None:
        """Return first element (successor of head)."""
        return self._first

    def pred(self) -> Link | None:
        """Return last element (predecessor of head)."""
        return self._last

    def first(self) -> Link | None:
        """Return first element in list."""
        return self._first

    def last(self) -> Link | None:
        """Return last element in list."""
        return self._last

    def empty(self) -> bool:
        """Check if list is empty."""
        return self._first is None

    def cardinal(self) -> int:
        """
        Return number of elements in list.

        From Head.cc:105-117.
        """
        count = 0
        current = self._first
        while current is not None:
            count += 1
            current = current.suc()
        return count

    def __len__(self) -> int:
        """Python-style length."""
        return self.cardinal()

    def __iter__(self) -> Iterator[Link]:
        """Iterate over elements from first to last."""
        current = self._first
        while current is not None:
            yield current
            current = current.suc()

    def add_first(self, element: Link | None) -> None:
        """
        Add element at start of list.

        From Head.cc:63-82.
        """
        if element is None:
            return

        if self._first is None:
            if element.in_list():
                element.out()
            self._first = element
            self._last = element
            element._the_list = self
        else:
            element.precede(self._first)
            self._first = element

    def add_last(self, element: Link | None) -> None:
        """
        Add element at end of list.

        From Head.cc:84-103.
        """
        if element is None:
            return

        if self._last is not None:
            element.follow(self._last)
            self._last = element
        else:
            if element.in_list():
                element.out()
            self._first = element
            self._last = element
            element._the_list = self

    def clear(self) -> None:
        """
        Remove all elements from list.

        Note: Unlike C++, Python doesn't delete the elements.
        They are just unlinked from this list.

        From Head.cc:119-131.
        """
        current = self._first
        while current is not None:
            next_elem = current.suc()
            current._the_list = None
            current._prev = None
            current._next = None
            current = next_elem

        self._first = None
        self._last = None

    def __str__(self) -> str:
        """String representation."""
        elements = list(self)
        return f"Head({len(elements)} elements)"
