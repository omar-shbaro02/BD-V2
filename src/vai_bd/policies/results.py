"""Shared results returned by deterministic policy functions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyCheck:
    """A non-throwing validation result with stable machine-readable reasons."""

    is_valid: bool
    reasons: tuple[str, ...] = ()
