import json

import pytest

from ai_writing_detector import DetectorConfig, load_config


def test_load_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"sameness_threshold": 4}), encoding="utf-8")

    config = load_config(path)

    assert config.sameness_threshold == 4
    assert config.profile_max_words["email_reply"] == 140


@pytest.mark.parametrize(
    "data",
    [
        {"sameness_threshold": 1},
        {"hard_phrases": "not-a-list"},
        {"profile_max_words": {"unknown": 10}},
        {"unexpected": True},
    ],
)
def test_invalid_config_is_rejected(data):
    with pytest.raises(ValueError):
        DetectorConfig.from_mapping(data)
