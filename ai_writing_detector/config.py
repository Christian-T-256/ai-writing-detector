"""Validated configuration for local policy extensions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Tuple

from .rules import PROFILES


def _phrase_tuple(value: Any, key: str) -> Tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    phrases = tuple(item.strip() for item in value if item.strip())
    if len(set(phrases)) != len(phrases):
        raise ValueError(f"{key} contains duplicate phrases")
    return phrases


@dataclass(frozen=True)
class DetectorConfig:
    """Options that tune batch comparison and add literal phrases."""

    hard_phrases: Tuple[str, ...] = ()
    soft_phrases: Tuple[str, ...] = ()
    sameness_threshold: int = 3
    opener_words: int = 8
    closing_words: int = 10
    profile_max_words: Mapping[str, int | None] = field(
        default_factory=lambda: {"email_reply": 140, "proposal": None, "website_copy": None}
    )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "DetectorConfig":
        if data is None:
            return cls()
        if not isinstance(data, Mapping):
            raise ValueError("config must be a JSON object")

        known = {
            "hard_phrases",
            "soft_phrases",
            "sameness_threshold",
            "opener_words",
            "closing_words",
            "profile_max_words",
        }
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"unknown config keys: {', '.join(unknown)}")

        def positive_int(key: str, default: int, minimum: int = 1) -> int:
            value = data.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{key} must be an integer >= {minimum}")
            return value

        max_words = {"email_reply": 140, "proposal": None, "website_copy": None}
        supplied_limits = data.get("profile_max_words", {})
        if not isinstance(supplied_limits, Mapping):
            raise ValueError("profile_max_words must be an object")
        for profile, value in supplied_limits.items():
            if profile not in PROFILES:
                raise ValueError(f"unknown profile in profile_max_words: {profile}")
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 1
            ):
                raise ValueError(f"profile_max_words.{profile} must be null or a positive integer")
            max_words[profile] = value

        return cls(
            hard_phrases=_phrase_tuple(data.get("hard_phrases"), "hard_phrases"),
            soft_phrases=_phrase_tuple(data.get("soft_phrases"), "soft_phrases"),
            sameness_threshold=positive_int("sameness_threshold", 3, 2),
            opener_words=positive_int("opener_words", 8),
            closing_words=positive_int("closing_words", 10),
            profile_max_words=max_words,
        )


def load_config(path: str | Path) -> DetectorConfig:
    """Load and validate a JSON configuration file."""

    config_path = Path(path)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"could not read config file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid config JSON at line {exc.lineno}, column {exc.colno}") from exc
    return DetectorConfig.from_mapping(data)


__all__ = ["DetectorConfig", "load_config"]
