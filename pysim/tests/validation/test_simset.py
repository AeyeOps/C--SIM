"""
Validation test for SimSet functionality.

Compares Python output against C++SIM Tests/SimSet/expected_output.

Expected output:
    Intersection is:
    value: 8
    value: 9
"""

import pytest

from pysim.simset import Head, Link


class Element(Link):
    """Simple element with an integer value, like C++ Element class."""

    def __init__(self, value: int) -> None:
        super().__init__()
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    def belongs(self, other_set: Head) -> bool:
        """Check if an element with the same value exists in other_set."""
        elem = other_set.first()
        while elem is not None:
            if isinstance(elem, Element) and elem.value == self._value:
                return True
            elem = elem.suc()
        return False


class TestSimSetExample:
    """Test replication of Tests/SimSet output."""

    def test_set_intersection(self) -> None:
        """Set intersection should produce values 8 and 9."""
        s1 = Head()
        s2 = Head()

        # S1 contains elements 0-9
        for i in range(10):
            e = Element(i)
            e.into(s1)

        # S2 contains elements 8-13
        for j in range(8, 14):
            e = Element(j)
            e.into(s2)

        # Compute intersection
        s3 = Head()
        elem = s1.first()
        while elem is not None:
            if isinstance(elem, Element) and elem.belongs(s2):
                new_elem = Element(elem.value)
                new_elem.into(s3)
            elem = elem.suc()

        # Verify intersection contains exactly 8 and 9
        result_values = []
        elem = s3.first()
        while elem is not None:
            if isinstance(elem, Element):
                result_values.append(elem.value)
            elem = elem.suc()

        assert result_values == [8, 9], f"Expected [8, 9], got {result_values}"

    def test_head_operations(self) -> None:
        """Test basic Head operations."""
        h = Head()
        assert h.empty()
        assert h.cardinal() == 0
        assert h.first() is None
        assert h.last() is None

        # Add elements
        e1 = Element(1)
        e2 = Element(2)
        e1.into(h)
        e2.into(h)

        assert not h.empty()
        assert h.cardinal() == 2
        assert h.first() is e1
        assert h.last() is e2

    def test_link_navigation(self) -> None:
        """Test Link suc/pred navigation."""
        h = Head()
        elements = [Element(i) for i in range(5)]
        for e in elements:
            e.into(h)

        # Test forward navigation
        current = h.first()
        for i, expected in enumerate(elements):
            assert current is expected
            current = current.suc()
        assert current is None

        # Test backward navigation
        current = h.last()
        for expected in reversed(elements):
            assert current is expected
            current = current.pred()
        assert current is None

    def test_link_precede_follow(self) -> None:
        """Test Link precede/follow insertion."""
        h = Head()
        e1 = Element(1)
        e2 = Element(2)
        e3 = Element(3)

        e2.into(h)  # [2]
        e1.precede(e2)  # [1, 2]
        e3.follow(e2)  # [1, 2, 3]

        values = []
        elem = h.first()
        while elem is not None:
            if isinstance(elem, Element):
                values.append(elem.value)
            elem = elem.suc()

        assert values == [1, 2, 3]

    def test_link_out(self) -> None:
        """Test Link removal."""
        h = Head()
        elements = [Element(i) for i in range(3)]
        for e in elements:
            e.into(h)

        # Remove middle element
        elements[1].out()

        values = []
        elem = h.first()
        while elem is not None:
            if isinstance(elem, Element):
                values.append(elem.value)
            elem = elem.suc()

        assert values == [0, 2]
        assert h.cardinal() == 2

    def test_link_in_list(self) -> None:
        """Test Link.in_list() status."""
        h = Head()
        e = Element(42)

        assert not e.in_list()
        e.into(h)
        assert e.in_list()
        e.out()
        assert not e.in_list()

    def test_head_clear(self) -> None:
        """Test Head.clear() removes all elements."""
        h = Head()
        elements = [Element(i) for i in range(5)]
        for e in elements:
            e.into(h)

        h.clear()

        assert h.empty()
        assert h.cardinal() == 0
        for e in elements:
            assert not e.in_list()
