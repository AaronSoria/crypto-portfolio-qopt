from __future__ import annotations

from qportfolio.problem.models.base import ConstraintSet


def build_constraint_set(**kwargs) -> ConstraintSet:
    return ConstraintSet(**kwargs)
