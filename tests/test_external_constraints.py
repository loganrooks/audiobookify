"""Fail the build when an externally-justified constraint goes stale.

See `external-constraints.toml` for the rationale. In short: constraints that
exist because of a fact about the outside world keep enforcing themselves after
that fact stops being true, and they look *more* justified the more they fail.
An expiry date is the cheapest mechanism that turns "we'll revisit this" into
something that actually interrupts someone.
"""

from __future__ import annotations

import datetime
import tomllib
from pathlib import Path

import pytest

CONSTRAINTS_FILE = Path(__file__).resolve().parent.parent / "external-constraints.toml"

REQUIRED_FIELDS = (
    "id",
    "claim",
    "applies_to",
    "verify",
    "evidence",
    "verified_on",
    "recheck_after",
    "owner",
)


def load_constraints() -> list[dict]:
    """Parse the constraint registry."""
    if not CONSTRAINTS_FILE.exists():
        return []
    with CONSTRAINTS_FILE.open("rb") as fh:
        return tomllib.load(fh).get("constraint", [])


CONSTRAINTS = load_constraints()


def constraint_ids() -> list[str]:
    return [c.get("id", f"constraint-{i}") for i, c in enumerate(CONSTRAINTS)]


def test_registry_exists_and_is_populated():
    """The registry should exist; an empty one is almost certainly a mistake."""
    assert CONSTRAINTS_FILE.exists(), f"missing {CONSTRAINTS_FILE.name}"
    assert CONSTRAINTS, "no constraints declared -- did the file get truncated?"


@pytest.mark.parametrize("constraint", CONSTRAINTS, ids=constraint_ids())
def test_constraint_is_fully_specified(constraint: dict):
    """A constraint nobody can re-check is indistinguishable from folklore."""
    missing = [f for f in REQUIRED_FIELDS if not constraint.get(f)]
    assert not missing, f"{constraint.get('id')!r} is missing: {', '.join(missing)}"


@pytest.mark.parametrize("constraint", CONSTRAINTS, ids=constraint_ids())
def test_constraint_dates_are_coherent(constraint: dict):
    """recheck_after must follow verified_on, or the expiry means nothing."""
    verified = constraint["verified_on"]
    recheck = constraint["recheck_after"]
    assert isinstance(verified, datetime.date), "verified_on must be a TOML date (YYYY-MM-DD)"
    assert isinstance(recheck, datetime.date), "recheck_after must be a TOML date (YYYY-MM-DD)"
    assert recheck > verified, (
        f"{constraint['id']!r}: recheck_after ({recheck}) must be after verified_on ({verified})"
    )


@pytest.mark.parametrize("constraint", CONSTRAINTS, ids=constraint_ids())
def test_constraint_has_not_gone_stale(constraint: dict):
    """The point of the whole file: expire claims about the outside world.

    If this fails, do NOT simply push the date out. Re-run the `verify` command
    and record what you actually observed in `evidence`. The failure is asking
    whether the claim is still true, not asking for a rubber stamp.
    """
    today = datetime.date.today()
    recheck = constraint["recheck_after"]
    if today > recheck:
        pytest.fail(
            f"Constraint {constraint['id']!r} went stale on {recheck} "
            f"({(today - recheck).days} days ago).\n\n"
            f"Claim: {constraint['claim'].strip()}\n\n"
            f"Re-verify with: {constraint['verify']}\n\n"
            "Then update verified_on, recheck_after, and evidence together in "
            "external-constraints.toml. Do not move the date without re-running "
            "the check -- that is exactly how the edge-tts pin survived seven "
            "months past its fix."
        )
