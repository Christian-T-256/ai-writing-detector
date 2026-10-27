"""Canonical writing rules.

The registry is data, while the matching engine lives in detector.py. Keeping those
concerns separate makes rule changes easy to review and test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


EMAIL_REPLY = "email_reply"
PROPOSAL = "proposal"
WEBSITE_COPY = "website_copy"
PROFILES = (EMAIL_REPLY, PROPOSAL, WEBSITE_COPY)
ALL_PROFILES = frozenset(PROFILES)


@dataclass(frozen=True)
class Rule:
    """One ordered regular-expression rule."""

    rule_id: str
    severity: str
    category: str
    pattern: str
    message: str
    suggestion: str
    profiles: FrozenSet[str] = ALL_PROFILES


def _hard(
    rule_id: str,
    category: str,
    pattern: str,
    message: str,
    suggestion: str,
    profiles: FrozenSet[str] = ALL_PROFILES,
) -> Rule:
    return Rule(rule_id, "hard", category, pattern, message, suggestion, profiles)


def _soft(
    rule_id: str,
    category: str,
    pattern: str,
    message: str,
    suggestion: str,
    profiles: FrozenSet[str] = ALL_PROFILES,
) -> Rule:
    return Rule(rule_id, "soft", category, pattern, message, suggestion, profiles)


# Order is intentional. Reports show punctuation and framing problems before
# vocabulary-level findings.
RULES = (
    _hard(
        "punctuation.dash",
        "punctuation",
        r"[\u2013\u2014]",
        "Em and en dashes are not allowed.",
        "Use a period, comma, colon, or parentheses.",
    ),
    _hard(
        "opening.filler",
        "filler opener",
        r"\b(?:i hope (?:this (?:email )?finds you well|you(?:'re| are) doing well)|"
        r"i wanted to reach out|i(?:'m| am) reaching out|thank you for reaching out|"
        r"thanks for sharing|i appreciate you sharing)\b",
        "The opening is a common filler phrase.",
        "Start with the specific reason for the message.",
    ),
    _hard(
        "opening.colon_drama",
        "colon drama",
        r"^[ \t]*(?:short version|quick version|quick one|the gist|bottom line|"
        r"long story short|net[ -]?net|in short|tl;?dr)[ \t]*[:,]",
        "The paragraph opens with a dramatic summary label.",
        "State the point directly without announcing it.",
    ),
    _hard(
        "closing.formal_signoff",
        "formal sign-off",
        r"^[ \t]*(?:best|warm|kind) regards[ \t]*,?[ \t]*$|"
        r"^[ \t]*sincerely[ \t]*,?[ \t]*$|^[ \t]*yours truly[ \t]*,?[ \t]*$",
        "The email uses a stock formal sign-off.",
        "Use a simple name-only sign-off or the sender's normal closing.",
        frozenset({EMAIL_REPLY}),
    ),
    _hard(
        "closing.filler",
        "filler closer",
        r"\b(?:looking forward to hearing|let me know if you have any questions|"
        r"don'?t hesitate to|feel free to)\b",
        "The closing uses a stock filler phrase.",
        "End with a concrete next step or a specific question.",
    ),
    _hard(
        "followup.generic_nudge",
        "generic follow-up",
        r"\b(?:just following up|following up here|bumping this|wanted to check "
        r"(?:in|whether|if)|just checking in|checking in on|any updates?)\b",
        "The follow-up does not add a specific reason to reply.",
        "Name the decision, deadline, or new information.",
        frozenset({EMAIL_REPLY}),
    ),
    _hard(
        "vocabulary.corporate_ai",
        "corporate AI vocabulary",
        r"\b(?:utilize|seamless|robust|delve|elevate|streamline|synergy|holistic|"
        r"cutting[ -]?edge|empower|facilitate|game[ -]?changer|supercharge|"
        r"deep dive|tailored solutions|leverage)\b",
        "The copy contains generic corporate vocabulary associated with AI drafts.",
        "Replace it with a concrete action, object, or result.",
    ),
    _hard(
        "vocabulary.llm_verbs",
        "LLM-style verb",
        r"\b(?:harness|capitalize on|unlock|catalyze|foster|bolster|underscore|"
        r"showcase|garner|embark|unpack)\b|\bdive into\b",
        "The copy uses a common LLM-style verb.",
        "Choose the plain verb that describes what happens.",
    ),
    _hard(
        "vocabulary.grandiose",
        "grandiose language",
        r"\b(?:vital|paramount|pivotal|profound|groundbreaking|transformative|"
        r"unprecedented|revolutionary|sophisticated|innovative|game[ -]?changing|"
        r"state[ -]of[ -]the[ -]art)\b",
        "The claim relies on an inflated adjective.",
        "Describe the observable benefit or evidence.",
    ),
    _hard(
        "vocabulary.poetic_noun",
        "abstract AI metaphor",
        r"\b(?:tapestry|labyrinth|crucible|realm|multifaceted|intricate|beacon|"
        r"symphony)\b|\bwoven into\b",
        "The copy uses an abstract metaphor common in generated writing.",
        "Name the concrete subject instead.",
    ),
    _hard(
        "tone.hollow_enthusiasm",
        "hollow enthusiasm",
        r"\b(?:delighted|thrilled|resonated)\b|\bstruck by\b|\bi love this\b|"
        r"\bthis is fantastic\b|\bkeeps me up at night\b|"
        r"\bwhat a (?:great|good) question\b|\bi(?:'d| would) be happy to\b",
        "The enthusiasm is generic rather than specific.",
        "Say what caught your attention and why.",
    ),
    _hard(
        "closing.faux_depth",
        "faux-depth closer",
        r"\b(?:there'?s more to unpack|food for thought|keep(?:ing)? the "
        r"conversation going|the conversation is just beginning|the future looks bright|"
        r"only time will tell)\b",
        "The closing gestures at depth without adding information.",
        "End on the decision, evidence, or next action.",
    ),
    _hard(
        "transition.mechanical",
        "mechanical transition",
        r"\b(?:furthermore|moreover|additionally|consequently)\b|"
        r"\bin conclusion\b|\bit bears mentioning\b|\bin today'?s\b|"
        r"\bin an era where\b",
        "The transition sounds formulaic.",
        "Join the ideas directly or use a plain connector.",
    ),
    _hard(
        "structure.scaffolding",
        "algorithmic scaffolding",
        r"\b(?:let'?s break this down|let me walk you through|let'?s dive in|"
        r"the bigger point|step back from)\b",
        "The copy announces its structure instead of making the point.",
        "Remove the announcement and begin with the substance.",
    ),
    _hard(
        "structure.inflation",
        "inflated construction",
        r"\b(?:serves as|stands as|boasts)\b",
        "The sentence uses an inflated construction.",
        "Prefer is, has, or a direct active verb.",
    ),
    _hard(
        "evidence.vague_attribution",
        "vague attribution",
        r"\b(?:experts (?:argue|say)|industry reports suggest|observers have cited|"
        r"studies show|research suggests)\b",
        "The claim cites unnamed evidence.",
        "Name the source or remove the attribution.",
    ),
    _hard(
        "structure.forced_contrast",
        "forced contrast",
        r"\bnot only .{1,60}? but(?: also)?\b|"
        r"\bit(?:'s| is) not just .{1,60}? it(?:'s| is)\b|"
        r"\bit isn'?t just .{1,60}? it(?:'s| is)\b|"
        r"\byou don'?t need .{1,60}?,? you need\b|"
        r"\bit(?:'s| is) not about .{1,60}?,? it(?:'s| is) about\b|"
        r"\b(?:most|many) (?:people|teams|companies) (?:think|believe|assume)\b",
        "The sentence uses a formulaic contrast frame.",
        "State the claim and its evidence without the setup.",
    ),
    _hard(
        "artifact.model_output",
        "model artifact",
        r"\b(?:contentreference|oaicite|oai_citation|turn\d+search\d+|"
        r"grok_render_citation_card_json|attached_file|ppl-ai-file-upload)\b|"
        r"\[cite:\s*\d+\]",
        "A model or chat interface artifact leaked into the copy.",
        "Remove the artifact and verify the surrounding claim.",
    ),
    _hard(
        "editorial.colon_drama",
        "colon drama",
        r"[.;:]\s+(?:the (?:result|difference|catch|point|best part|kicker)|"
        r"here'?s the (?:thing|kicker))\s*[:?]",
        "The copy uses a staged colon or question reveal.",
        "Combine the thought into one direct sentence.",
        frozenset({PROPOSAL, WEBSITE_COPY}),
    ),
    _soft(
        "style.adverb_stack",
        "intensifier adverb",
        r"\b(?:literally|genuinely|truly|deeply|fundamentally|inherently|"
        r"inevitably|interestingly|importantly|crucially|remarkably|arguably|"
        r"notably|surprisingly|frankly)\b",
        "This adverb may add emphasis without meaning.",
        "Delete it and check whether the sentence changes.",
    ),
    _soft(
        "tone.hedge",
        "generic emphasis",
        r"\b(?:ultimately|to be honest|let me be clear|that'?s exactly|absolutely)\b|"
        r"\b100%\b",
        "The phrase adds generic emphasis.",
        "Use evidence or remove the phrase.",
    ),
    _soft(
        "style.abstract_metaphor",
        "abstract metaphor",
        r"\b(?:nuanced|landscape|journey|narrative|ecosystem)\b",
        "The word is broad enough to hide the actual point.",
        "Use the name of the process, market, or event.",
    ),
    _soft(
        "style.brochure_language",
        "brochure language",
        r"\b(?:nestled|renowned|breathtaking|must[ -]?visit|stunning|exemplifies|"
        r"vibrant)\b|\bin the heart of\b|\bnatural beauty\b|\bdiverse array\b",
        "The description sounds like generic brochure copy.",
        "Replace the adjective with a verifiable detail.",
        frozenset({PROPOSAL, WEBSITE_COPY}),
    ),
    _soft(
        "structure.participle_tail",
        "participial tail",
        r",\s+(?:highlighting|underscoring|emphasizing|reflecting|symbolizing|"
        r"showcasing|ensuring|fostering|cultivating|encompassing|enhancing|"
        r"contributing to|solidifying|reinforcing)\b",
        "The sentence ends with a generic participial add-on.",
        "Make the relationship explicit or split the sentence.",
        frozenset({PROPOSAL, WEBSITE_COPY}),
    ),
    _soft(
        "structure.signposting",
        "signposting announcement",
        r"\b(?:let'?s explore|here'?s what you need to know|now let'?s look at|"
        r"without further ado|let'?s take a look)\b",
        "The copy announces what comes next.",
        "Start with the information itself.",
    ),
    _soft(
        "style.verbose_filler",
        "verbose filler",
        r"\b(?:in order to|due to the fact that|at this point in time|"
        r"in the event that|has the ability to|it (?:is|should be) important to note)\b",
        "A shorter phrase would say the same thing.",
        "Use to, because, now, if, can, or remove the phrase.",
    ),
    _soft(
        "style.stacked_hedging",
        "stacked hedging",
        r"\b(?:could potentially|may possibly|might possibly|it could be argued|"
        r"perhaps you (?:may|might))\b",
        "The sentence stacks multiple hedges.",
        "Keep one qualifier if uncertainty matters.",
    ),
    _soft(
        "opening.email_filler",
        "email filler",
        r"\b(?:happy to|glad you reached out|perfect timing|"
        r"(?:good|fair|great) question)\b",
        "The phrase acknowledges the message without adding much.",
        "Respond to the specific detail instead.",
        frozenset({EMAIL_REPLY}),
    ),
    _soft(
        "punctuation.curly_quotes",
        "curly quotation marks",
        r"[\u201c\u201d]",
        "Curly quotation marks can create inconsistent pasted copy.",
        "Use straight quotation marks if the publishing system requires them.",
        frozenset({PROPOSAL, WEBSITE_COPY}),
    ),
)


__all__ = [
    "ALL_PROFILES",
    "EMAIL_REPLY",
    "PROFILES",
    "PROPOSAL",
    "RULES",
    "Rule",
    "WEBSITE_COPY",
]
