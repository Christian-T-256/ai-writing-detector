"""Stable human-readable output for local runs and CI logs."""

from __future__ import annotations

from typing import Any, Mapping


def render_text(report: Mapping[str, Any]) -> str:
    """Render a report without terminal colors or environment-specific markup."""

    summary = report["summary"]
    lines = [
        f"AI Writing Detector: {'PASS' if report['clean'] else 'FAIL'}",
        f"Profile: {report['profile']}",
        (
            "Summary: "
            f"drafts={summary['drafts']} hard={summary['hard']} soft={summary['soft']} "
            f"sameness={summary['sameness']}"
        ),
    ]

    for draft in report["drafts"]:
        lines.extend(
            [
                "",
                f"Draft {draft['id']}: {'PASS' if draft['clean'] else 'FAIL'} "
                f"({draft['word_count']} words)",
            ]
        )
        if not draft["findings"]:
            lines.append("  No findings.")
            continue
        for finding in draft["findings"]:
            lines.append(
                f"  [{finding['severity'].upper()}] {finding['rule_id']} "
                f"at {finding['line']}:{finding['column']}: {finding['message']}"
            )
            if finding["match"]:
                lines.append(f"    Match: {finding['match']!r}")
            lines.append(f"    Fix: {finding['suggestion']}")

    if report["sameness"]:
        lines.extend(["", "Cross-draft sameness:"])
        for finding in report["sameness"]:
            ids = ", ".join(finding["draft_ids"])
            lines.append(
                f"  [HARD] {finding['kind']} repeated {finding['count']} times "
                f"in {ids}: {finding['text']!r}"
            )

    return "\n".join(lines)


__all__ = ["render_text"]
