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
