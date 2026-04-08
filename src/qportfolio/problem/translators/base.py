from __future__ import annotations

from typing import Any, Dict


class ProblemTranslator:
    target_type: str = "base"

    def translate(self, problem) -> Dict[str, Any]:
        raise NotImplementedError
