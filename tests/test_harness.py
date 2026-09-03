"""Proves the test harness runs."""

from __future__ import annotations


def test_harness_collects_and_runs() -> None:
    """Smoke test: proves pytest discovers and executes this directory.

    Asserts a constant deliberately — the assertion under test is the runner
    itself, not the expression.
    """
    assert True
