"""Pure linting functions for single drafts and batches."""

from __future__ import annotations

import re
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable, Mapping, Sequence

from .config import DetectorConfig
from .rules import PROFILES, PROPOSAL, RULES, WEBSITE_COPY, Rule


_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}|\[INSERT[^\]]*\]|\bTODO\b|\bTBD\b", re.IGNORECASE)
_COMPILED_RULES = tuple((rule, re.compile(rule.pattern, re.IGNORECASE | re.MULTILINE)) for rule in RULES)
_IGNORED_HTML_TAGS = frozenset({"script", "style", "blockquote"})
_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "p",
        "section",
        "td",
        "th",
        "tr",
    }
)


class _VisibleTextParser(HTMLParser):
    """Extract authored text while ignoring code, styles, and quoted testimonials."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored: Counter[str] = Counter()

    @property
    def is_ignored(self) -> bool:
        return bool(self.ignored)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _IGNORED_HTML_TAGS:
            self.ignored[tag] += 1
            return
        if tag in _BLOCK_TAGS and not self.is_ignored:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _BLOCK_TAGS and not self.is_ignored:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _IGNORED_HTML_TAGS and self.ignored[tag]:
            self.ignored[tag] -= 1
            if self.ignored[tag] == 0:
                del self.ignored[tag]
            return
        if tag in _BLOCK_TAGS and not self.is_ignored:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.is_ignored:
            self.parts.append(data)

    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line)


def _config(value: DetectorConfig | Mapping[str, Any] | None) -> DetectorConfig:
    if value is None:
        return DetectorConfig()
    if isinstance(value, DetectorConfig):
        return value
    return DetectorConfig.from_mapping(value)


def _visible_text(text: str, profile: str) -> str:
    if profile not in {PROPOSAL, WEBSITE_COPY}:
        return text
    parser = _VisibleTextParser()
    try:
        parser.feed(text)
        parser.close()
    except (ValueError, AssertionError):
        # HTMLParser is forgiving, but malformed character references can still
        # fail. Falling back to the original text keeps the gate fail-safe.
        return unescape(text)
    if parser.ignored:
        # An unclosed ignored region must not hide the rest of a page from the
        # detector. Scanning the raw text may be noisy, but it cannot fail open.
        return unescape(text)
    return parser.text()


def _location(text: str, start: int) -> tuple[int, int]:
    line = text.count("\n", 0, start) + 1
    previous_newline = text.rfind("\n", 0, start)
    column = start + 1 if previous_newline < 0 else start - previous_newline
    return line, column


def _finding(rule: Rule, match: re.Match[str], text: str) -> dict[str, Any]:
    line, column = _location(text, match.start())
    return {
        "rule_id": rule.rule_id,
        "severity": rule.severity,
        "category": rule.category,
        "message": rule.message,
        "match": match.group(0)[:80],
        "line": line,
        "column": column,
        "suggestion": rule.suggestion,
    }


def _structural_finding(
    rule_id: str,
    severity: str,
    category: str,
    message: str,
    match: str,
    suggestion: str,
    line: int = 1,
    column: int = 1,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "category": category,
        "message": message,
        "match": match[:80],
        "line": line,
        "column": column,
        "suggestion": suggestion,
    }


def _custom_findings(text: str, config: DetectorConfig) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for severity, phrases in (("hard", config.hard_phrases), ("soft", config.soft_phrases)):
        for index, phrase in enumerate(phrases, start=1):
            pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
            match = pattern.search(text)
            if not match:
                continue
            line, column = _location(text, match.start())
            findings.append(
                _structural_finding(
                    f"custom.{severity}.{index}",
                    severity,
                    "custom phrase",
                    f"The copy contains a configured {severity} phrase.",
                    match.group(0),
                    "Replace the phrase according to the local style guide.",
                    line,
                    column,
                )
            )
    return findings


def _draft_data(item: str | Mapping[str, Any], index: int) -> dict[str, str]:
    if isinstance(item, str):
        return {"id": f"draft-{index}", "text": item}
    if not isinstance(item, Mapping):
        raise ValueError(f"draft {index} must be a string or object")
    text = item.get("text", item.get("draft"))
    if text is None:
        raise ValueError(f"draft {index} must contain a text or draft field")
    if not isinstance(text, str):
        raise ValueError(f"draft {index} text must be a string")
    draft_id = item.get("id") or item.get("to") or item.get("name") or f"draft-{index}"
    if not isinstance(draft_id, str):
        raise ValueError(f"draft {index} id must be a string")
    return {"id": draft_id, "text": text}


def _lint_one(
    draft: Mapping[str, str],
    profile: str,
    config: DetectorConfig,
    fail_on_soft: bool,
) -> tuple[dict[str, Any], str]:
    raw_text = draft["text"]
    text = _visible_text(raw_text, profile)
    findings: list[dict[str, Any]] = []

    if not raw_text.strip():
        findings.append(
            _structural_finding(
                "content.empty",
                "hard",
                "missing content",
                "The draft is empty.",
                "",
                "Add the customer-facing copy before running the gate.",
            )
        )

    for rule, pattern in _COMPILED_RULES:
        if profile not in rule.profiles:
            continue
        match = pattern.search(text)
        if match:
            findings.append(_finding(rule, match, text))

    if profile == PROPOSAL:
        placeholder = _PLACEHOLDER_RE.search(raw_text)
        if placeholder:
            line, column = _location(raw_text, placeholder.start())
            findings.append(
                _structural_finding(
                    "proposal.placeholder",
                    "hard",
                    "unfilled placeholder",
                    "The proposal still contains a template placeholder.",
                    placeholder.group(0),
                    "Replace the token with reviewed customer-specific content.",
                    line,
                    column,
                )
            )

    findings.extend(_custom_findings(text, config))
    word_count = len(_WORD_RE.findall(text))
    max_words = config.profile_max_words.get(profile)
    if max_words is not None and word_count > max_words:
        findings.append(
            _structural_finding(
                "length.too_long",
                "soft",
                "length",
                f"The draft has {word_count} words; this profile recommends {max_words} or fewer.",
                "",
                "Cut repeated context and keep the requested action visible.",
            )
        )

    hard_count = sum(finding["severity"] == "hard" for finding in findings)
    soft_count = sum(finding["severity"] == "soft" for finding in findings)
    result = {
        "id": draft["id"],
        "clean": hard_count == 0 and (not fail_on_soft or soft_count == 0),
        "word_count": word_count,
        "hard_count": hard_count,
        "soft_count": soft_count,
        "findings": findings,
    }
    return result, text


def _normalised_words(text: str, limit: int, tail: bool = False) -> str:
    words = [word.lower() for word in _WORD_RE.findall(text)]
    selected = words[-limit:] if tail else words[:limit]
    return " ".join(selected)


def _opener(text: str, word_limit: int) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    first = lines[0]
    if re.fullmatch(r"(?:hi|hey|hello)\s+.{1,40}[,!]", first, re.IGNORECASE):
        if len(lines) == 1:
            return ""
        first = lines[1]
    else:
        first = re.sub(
            r"^(?:hi|hey|hello)\s+(?:\{\{[^}]+\}\}|[a-z][a-z'.-]*)[,!]\s*",
            "",
            first,
            flags=re.IGNORECASE,
        )
    return _normalised_words(first, word_limit)


def _closing_ask(text: str, word_limit: int) -> str:
    questions = re.findall(r"[^.!?\n]*\?", text)
    if not questions:
        return ""
    return _normalised_words(questions[-1], word_limit, tail=True)


def _sameness(
    drafts: Sequence[Mapping[str, str]],
    visible_texts: Sequence[str],
    config: DetectorConfig,
) -> list[dict[str, Any]]:
    values: dict[str, list[tuple[str, str]]] = {"opener": [], "closing_ask": []}
    for draft, text in zip(drafts, visible_texts):
        values["opener"].append((draft["id"], _opener(text, config.opener_words)))
        values["closing_ask"].append((draft["id"], _closing_ask(text, config.closing_words)))

    findings: list[dict[str, Any]] = []
    for kind, rows in values.items():
        counts = Counter(value for _, value in rows if value)
        for value, count in sorted(counts.items()):
            if count < config.sameness_threshold:
                continue
            findings.append(
                {
                    "kind": kind,
                    "text": value,
                    "count": count,
                    "draft_ids": [draft_id for draft_id, row_value in rows if row_value == value],
                    "message": (
                        "The same opening is repeated across the batch."
                        if kind == "opener"
                        else "The same closing ask is repeated across the batch."
                    ),
                }
            )
    return findings


def lint_batch(
    drafts: Iterable[str | Mapping[str, Any]],
    profile: str = "email_reply",
    *,
    config: DetectorConfig | Mapping[str, Any] | None = None,
    fail_on_soft: bool = False,
) -> dict[str, Any]:
    """Lint a batch and return a JSON-serializable report.

    Hard findings and cross-draft sameness fail the gate. Soft findings fail only
    when ``fail_on_soft`` is true.
    """

    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose one of {', '.join(PROFILES)}")
    settings = _config(config)
    normalised = [_draft_data(item, index) for index, item in enumerate(drafts, start=1)]
    if not normalised:
        raise ValueError("at least one draft is required")
    ids = [draft["id"] for draft in normalised]
    duplicates = sorted(draft_id for draft_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"draft ids must be unique: {', '.join(duplicates)}")

    results: list[dict[str, Any]] = []
    visible_texts: list[str] = []
    for draft in normalised:
        result, visible = _lint_one(draft, profile, settings, fail_on_soft)
        results.append(result)
        visible_texts.append(visible)

    sameness = _sameness(normalised, visible_texts, settings)
    hard_count = sum(result["hard_count"] for result in results)
    soft_count = sum(result["soft_count"] for result in results)
    blocking_issues = hard_count + len(sameness) + (soft_count if fail_on_soft else 0)
    return {
        "clean": blocking_issues == 0,
        "profile": profile,
        "fail_on_soft": fail_on_soft,
        "summary": {
            "drafts": len(results),
            "hard": hard_count,
            "soft": soft_count,
            "sameness": len(sameness),
            "blocking_issues": blocking_issues,
        },
        "drafts": results,
        "sameness": sameness,
    }


def lint_text(
    text: str,
    profile: str = "email_reply",
    *,
    draft_id: str = "draft-1",
    config: DetectorConfig | Mapping[str, Any] | None = None,
    fail_on_soft: bool = False,
) -> dict[str, Any]:
    """Lint one string using the same report contract as ``lint_batch``."""

    return lint_batch(
        [{"id": draft_id, "text": text}],
        profile,
        config=config,
        fail_on_soft=fail_on_soft,
    )


__all__ = ["lint_batch", "lint_text"]
