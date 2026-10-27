import json

import pytest

from ai_writing_detector import DetectorConfig, lint_batch, lint_text


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("A clear plan\u2014with one owner.", "punctuation.dash"),
        ("A clear plan\u2013with one owner.", "punctuation.dash"),
        ("I hope this email finds you well.", "opening.filler"),
        ("Quick version: the file is ready.", "opening.colon_drama"),
        ("We offer a robust process.", "vocabulary.corporate_ai"),
        ("Let me walk you through the plan.", "structure.scaffolding"),
        ("Studies show this works.", "evidence.vague_attribution"),
        ("It is not just a report, it's a roadmap.", "structure.forced_contrast"),
        ("See turn4search2 for the source.", "artifact.model_output"),
    ],
)
def test_hard_rules_block(text, rule_id):
    report = lint_text(text)

    assert report["clean"] is False
    assert rule_id in {finding["rule_id"] for finding in report["drafts"][0]["findings"]}


def test_clean_reply_passes():
    report = lint_text(
        "Hi Jamie,\n\nThe revised form is ready. Can you check the question order?\n\nMorgan"
    )

    assert report["clean"] is True
    assert report["summary"] == {
        "drafts": 1,
        "hard": 0,
        "soft": 0,
        "sameness": 0,
        "blocking_issues": 0,
    }


def test_soft_findings_warn_by_default_and_can_fail():
    warning = lint_text("Frankly, the draft needs one more example.")
    strict = lint_text("Frankly, the draft needs one more example.", fail_on_soft=True)

    assert warning["clean"] is True
    assert warning["summary"]["soft"] == 1
    assert strict["clean"] is False
    assert strict["summary"]["blocking_issues"] == 1


def test_formal_signoff_is_email_only():
    text = "The scope is ready.\n\nBest regards,\nMorgan"

    email = lint_text(text, profile="email_reply")
    proposal = lint_text(text, profile="proposal")

    assert "closing.formal_signoff" in {
        finding["rule_id"] for finding in email["drafts"][0]["findings"]
    }
    assert "closing.formal_signoff" not in {
        finding["rule_id"] for finding in proposal["drafts"][0]["findings"]
    }


def test_proposal_blocks_placeholders():
    report = lint_text(
        "The implementation starts on [INSERT DATE]. Owner: TODO.",
        profile="proposal",
    )

    assert report["clean"] is False
    assert "proposal.placeholder" in {
        finding["rule_id"] for finding in report["drafts"][0]["findings"]
    }


def test_website_ignores_quotes_scripts_and_attributes():
    html = (
        '<section class="robust"><h1>Scheduling that fits your front desk</h1>'
        '<blockquote>They gave us a seamless process.</blockquote>'
        '<script>const label = "transformative";</script>'
        '<p>Patients can request a time online.</p></section>'
    )

    report = lint_text(html, profile="website_copy")

    assert report["summary"]["hard"] == 0


def test_website_decodes_entity_dashes():
    report = lint_text(
        "<p>Appointments are confirmed &mdash; before the patient leaves.</p>",
        profile="website_copy",
    )

    assert "punctuation.dash" in {
        finding["rule_id"] for finding in report["drafts"][0]["findings"]
    }


def test_unclosed_ignored_html_region_fails_open_to_raw_scan():
    report = lint_text(
        "<h1>Scheduling</h1><blockquote>Quoted text<p>A robust process.",
        profile="website_copy",
    )

    assert "vocabulary.corporate_ai" in {
        finding["rule_id"] for finding in report["drafts"][0]["findings"]
    }


def test_custom_phrases_and_length_limit():
    config = DetectorConfig.from_mapping(
        {
            "hard_phrases": ["clear skies ahead"],
            "soft_phrases": ["next-level"],
            "profile_max_words": {"email_reply": 3},
        }
    )
    report = lint_text(
        "Clear skies ahead with a next-level plan.",
        config=config,
    )
    rule_ids = {finding["rule_id"] for finding in report["drafts"][0]["findings"]}

    assert "custom.hard.1" in rule_ids
    assert "custom.soft.1" in rule_ids
    assert "length.too_long" in rule_ids


def test_batch_flags_repeated_openers_and_closing_asks():
    drafts = [
        {
            "id": f"draft-{index}",
            "text": (
                f"Hi Person{index},\n\nThe revised schedule is ready for review. "
                "Can you approve it by Friday?\n\nMorgan"
            ),
        }
        for index in range(1, 4)
    ]

    report = lint_batch(drafts)

    assert report["clean"] is False
    assert {finding["kind"] for finding in report["sameness"]} == {
        "opener",
        "closing_ask",
    }
    assert report["summary"]["hard"] == 0
    assert report["summary"]["sameness"] == 2


def test_sameness_threshold_is_configurable():
    drafts = [
        {"id": "one", "text": "The revised schedule is ready. Can you approve it?"},
        {"id": "two", "text": "The revised schedule is ready. Can you approve it?"},
    ]

    default = lint_batch(drafts)
    strict = lint_batch(drafts, config={"sameness_threshold": 2})

    assert default["clean"] is True
    assert strict["clean"] is False
    assert strict["summary"]["sameness"] == 2


def test_report_is_json_serializable():
    report = lint_text("The requested changes are ready.")

    assert json.loads(json.dumps(report)) == report


def test_empty_draft_is_a_hard_failure():
    report = lint_text("")

    assert report["clean"] is False
    assert report["drafts"][0]["findings"][0]["rule_id"] == "content.empty"


def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        lint_batch([{"id": "same", "text": "One"}, {"id": "same", "text": "Two"}])


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError, match="unknown profile"):
        lint_text("Draft", profile="social_post")
