"""Shared fixtures.

`career` is a fresh synthetic career built per test, so tests can mutate and
save it freely without touching each other or needing a real game save.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import fixture  # noqa: E402  (needs the path insert above)

from pcmdb.model import Career  # noqa: E402


@pytest.fixture
def career_path(tmp_path):
    """Path to a freshly written synthetic career .cdb."""
    return fixture.write(tmp_path / "synthetic.cdb")


@pytest.fixture
def career(career_path):
    """A loaded synthetic Career, isolated per test."""
    return Career.load(career_path)


def reload_career(car, tmp_path, name="saved.cdb"):
    """Save `car` and load it back — the round-trip every editor action must survive."""
    out = tmp_path / name
    car.save(str(out))
    return Career.load(str(out))


def rider_id(car, last):
    """Look a rider up by surname, so tests survive fixture reshuffles."""
    for rid, r in car.riders.items():
        if r["last"] == last:
            return rid
    raise KeyError("no rider %r in fixture" % last)


def race_id(car, name):
    for rid, r in car.races.items():
        if r["name"] == name:
            return rid
    raise KeyError("no race %r in fixture" % name)


@pytest.fixture
def climber(career):
    """The team-1 climbing leader."""
    return rider_id(career, "Bergman")


@pytest.fixture
def cobbler(career):
    """The team-1 cobbled-classics leader."""
    return rider_id(career, "Kassei")
