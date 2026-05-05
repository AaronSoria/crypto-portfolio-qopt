"""
Pasqal Cloud credentials loader.

Priority order (highest to lowest):
  1. Explicit arguments passed to PasqalCredentials()
  2. Environment variables (PASQAL_USERNAME, PASQAL_PASSWORD, PASQAL_PROJECT_ID)
  3. .env.pasqal file in the project root (or path set via PASQAL_ENV_FILE)

Usage:
    from qopt.credentials import PasqalCredentials
    creds = PasqalCredentials.load()
    sdk = SDK(username=creds.username, password=creds.password, project_id=creds.project_id)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Default locations to search for the credentials file
_DEFAULT_ENV_FILE = ".env.pasqal"
_ENV_FILE_ENV_VAR = "PASQAL_ENV_FILE"


def _find_env_file() -> Optional[Path]:
    """
    Search for .env.pasqal walking up from cwd to repo root.
    Also checks the path set in PASQAL_ENV_FILE env var.
    """
    # Explicit override
    explicit = os.environ.get(_ENV_FILE_ENV_VAR)
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None

    # Walk up from cwd
    search = Path.cwd()
    for _ in range(6):  # max 6 levels up
        candidate = search / _DEFAULT_ENV_FILE
        if candidate.exists():
            return candidate
        parent = search.parent
        if parent == search:
            break
        search = parent
    return None


def _parse_env_file(path: Path) -> dict:
    """Parse a simple KEY=value file, ignoring comments and blank lines."""
    values = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                values[key] = val
    return values


@dataclass
class PasqalCredentials:
    username:   str
    password:   str
    project_id: str

    @classmethod
    def load(
        cls,
        username:   Optional[str] = None,
        password:   Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> "PasqalCredentials":
        """
        Load credentials with priority:
          explicit args > env vars > .env.pasqal file
        """
        # Start with file values (lowest priority)
        file_values: dict = {}
        env_file = _find_env_file()
        if env_file:
            file_values = _parse_env_file(env_file)
            print(f"  [credentials] loaded from {env_file}")
        else:
            print("  [credentials] no .env.pasqal found — using env vars only")

        def resolve(arg: Optional[str], env_key: str, file_key: str) -> str:
            return (
                arg
                or os.environ.get(env_key, "")
                or file_values.get(file_key, "")
            )

        u = resolve(username,   "PASQAL_USERNAME",   "PASQAL_USERNAME")
        p = resolve(password,   "PASQAL_PASSWORD",   "PASQAL_PASSWORD")
        pid = resolve(project_id, "PASQAL_PROJECT_ID", "PASQAL_PROJECT_ID")

        return cls(username=u, password=p, project_id=pid)

    def validate(self) -> None:
        """Raise ValueError if any required credential is missing."""
        missing = [
            name for name, val in [
                ("PASQAL_USERNAME",   self.username),
                ("PASQAL_PASSWORD",   self.password),
                ("PASQAL_PROJECT_ID", self.project_id),
            ] if not val
        ]
        if missing:
            raise ValueError(
                f"Missing Pasqal credentials: {missing}\n"
                f"Set them in .env.pasqal (see .env.pasqal.example) or as env vars."
            )

    def is_complete(self) -> bool:
        return bool(self.username and self.password and self.project_id)

    def masked(self) -> dict:
        """Safe representation for logging — never exposes password."""
        return {
            "username":   self.username,
            "password":   "***" if self.password else "(not set)",
            "project_id": self.project_id,
        }
