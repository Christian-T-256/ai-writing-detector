"""Command-line interface for files, standard input, and the built-in demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import load_config
from .detector import lint_batch
from .reporting import render_text
from .rules import PROFILES
from .samples import DEMO_DRAFTS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-writing-detector",
        description="Flag deterministic AI-writing tells in customer-facing drafts.",
    )
    parser.add_argument("input", nargs="?", help="JSON file to lint, or - for standard input")
    parser.add_argument("--demo", action="store_true", help="lint built-in fictional drafts")
    parser.add_argument("--profile", choices=PROFILES, default="email_reply")
    parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    parser.add_argument("--config", help="optional JSON policy file")
    parser.add_argument("--soft-fail", action="store_true", help="make soft warnings fail the gate")
    return parser


def _read_json(path: str) -> Any:
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"could not read input: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid input JSON at line {exc.lineno}, column {exc.colno}") from exc


def _drafts_from_json(data: Any) -> list[str | Mapping[str, Any]]:
    if isinstance(data, list):
        return data
    if not isinstance(data, Mapping):
        raise ValueError("input JSON must be a list or object")
    if isinstance(data.get("drafts"), list):
        return data["drafts"]
    if "text" in data or "draft" in data:
        return [data]
    if data and all(isinstance(value, Mapping) for value in data.values()):
        drafts: list[Mapping[str, Any]] = []
        for draft_id, value in data.items():
            row = dict(value)
            row.setdefault("id", str(draft_id))
            drafts.append(row)
        return drafts
    raise ValueError("input object must contain drafts, text, or draft")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.demo and args.input:
        parser.error("--demo cannot be combined with an input file")
    if not args.demo and not args.input:
        parser.error("provide an input file, - for standard input, or --demo")

    try:
        drafts = DEMO_DRAFTS if args.demo else _drafts_from_json(_read_json(args.input))
        config = load_config(args.config) if args.config else None
        report = lint_batch(
            drafts,
            profile=args.profile,
            config=config,
            fail_on_soft=args.soft_fail,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output_format == "json":
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(render_text(report))
    return 0 if report["clean"] else 1


__all__ = ["main"]
