from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from agent.profile import AgentProfile


class ProfileValidationError(Exception):
    """Raised when a profile YAML file is invalid."""

    def __init__(self, file_path: str, errors: list) -> None:
        self.file_path = file_path
        self.errors = errors
        super().__init__(f"Profile validation failed for {file_path}: {errors}")


class ProfileLoader:
    """Loads and validates agent profiles from YAML files."""

    def __init__(self, profiles_dir: str = "config/agents") -> None:
        self.profiles_dir = Path(profiles_dir)
        self._profiles: dict[str, AgentProfile] = {}

    def load_all(self) -> dict[str, AgentProfile]:
        """Load all profile YAML files from the profiles directory.

        Raises ProfileValidationError if any file is invalid.
        """
        self._profiles = {}

        if not self.profiles_dir.exists():
            return self._profiles

        for yaml_file in self.profiles_dir.glob("*.yaml"):
            profile = self._load_one(yaml_file)
            self._profiles[profile.id] = profile

        return self._profiles

    def _load_one(self, file_path: Path) -> AgentProfile:
        """Load and validate a single profile YAML file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ProfileValidationError(str(file_path), [f"YAML parse error: {e}"])

        if not isinstance(data, dict):
            raise ProfileValidationError(str(file_path), ["YAML root must be a mapping"])

        data = self._apply_env_overrides(data)

        try:
            return AgentProfile(**data)
        except ValidationError as e:
            raise ProfileValidationError(str(file_path), e.errors())

    @staticmethod
    def _apply_env_overrides(data: dict) -> dict:
        """Apply optional per-profile LLM overrides from environment variables."""
        profile_id = str(data.get("id", "")).upper().replace("-", "_")
        if not profile_id:
            return data

        llm_data = dict(data.get("llm") or {})
        fallback_data = dict(llm_data.get("fallback") or {})
        fields = {
            "provider": "PROVIDER",
            "model": "MODEL",
            "temperature": "TEMPERATURE",
        }
        for field, suffix in fields.items():
            value = os.getenv(f"CAPYMOCK_{profile_id}_{suffix}")
            if value:
                llm_data[field] = value

            fallback_value = os.getenv(f"CAPYMOCK_{profile_id}_FALLBACK_{suffix}")
            if fallback_value:
                fallback_data[field] = fallback_value

        if fallback_data:
            llm_data["fallback"] = fallback_data
        data["llm"] = llm_data
        return data

    def get(self, profile_id: str) -> AgentProfile | None:
        """Get a profile by ID."""
        return self._profiles.get(profile_id)

    def all(self) -> list[AgentProfile]:
        """Get all loaded profiles."""
        return list(self._profiles.values())
