"""
Pytest configuration and fixtures for PySim validation.
"""

import re
from pathlib import Path
from typing import Callable

import pytest
import simpy

CPPSIM_ROOT = Path("/opt/dev/cppsim")


@pytest.fixture
def expected_output() -> Callable[[str], str]:
    """Load expected output for a test case."""

    def _load(name: str) -> str:
        path = CPPSIM_ROOT / name / "expected_output"
        if not path.exists():
            pytest.skip(f"Expected output not found: {path}")
        return path.read_text()

    return _load


@pytest.fixture
def env() -> simpy.Environment:
    """Create a fresh SimPy environment."""
    return simpy.Environment()


def assert_numeric_match(
    actual: str,
    expected: str,
    atol: float = 1e-4,
    rtol: float = 1e-6,
    section: str | None = None,
) -> None:
    """
    Extract numbers and compare with tolerance.

    Args:
        actual: Actual output string
        expected: Expected output string
        atol: Absolute tolerance
        rtol: Relative tolerance
        section: Optional section header to extract from expected
    """
    if section:
        # Extract section from expected output
        lines = expected.split("\n")
        in_section = False
        section_lines = []
        for line in lines:
            if section in line:
                in_section = True
                continue
            if in_section:
                if line.strip() and not line.startswith(" ") and ":" not in line:
                    break
                section_lines.append(line)
        expected = "\n".join(section_lines)

    # Extract all numbers (including negative and decimal)
    num_pattern = r"-?\d+\.?\d*(?:[eE][+-]?\d+)?"
    actual_nums = [float(x) for x in re.findall(num_pattern, actual)]
    expected_nums = [float(x) for x in re.findall(num_pattern, expected)]

    assert len(actual_nums) == len(expected_nums), (
        f"Number count mismatch: {len(actual_nums)} vs {len(expected_nums)}"
    )

    for i, (a, e) in enumerate(zip(actual_nums, expected_nums)):
        diff = abs(a - e)
        threshold = atol + rtol * abs(e)
        assert diff <= threshold, f"Mismatch at index {i}: {a} != {e} (diff={diff}, threshold={threshold})"


def assert_output_matches(
    actual: str,
    expected: str,
    section: str | None = None,
    atol: float = 1e-4,
    rtol: float = 1e-6,
) -> None:
    """
    Compare simulation output with expected output.

    Args:
        actual: Actual output string
        expected: Expected output string
        section: Optional section to extract
        atol: Absolute tolerance for numeric comparison
        rtol: Relative tolerance for numeric comparison
    """
    assert_numeric_match(actual, expected, atol=atol, rtol=rtol, section=section)
