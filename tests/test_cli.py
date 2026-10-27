import json
import subprocess
import sys


def run_cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "ai_writing_detector", *args],
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )


def test_demo_prints_report_and_fails_gate():
    result = run_cli("--demo")

    assert result.returncode == 1
    assert "AI Writing Detector: FAIL" in result.stdout
    assert "Draft clean-reply: PASS" in result.stdout
    assert "Cross-draft sameness:" in result.stdout


def test_json_output_is_machine_readable():
    result = run_cli("--demo", "--format", "json")
    report = json.loads(result.stdout)

    assert result.returncode == 1
    assert report["profile"] == "email_reply"
    assert report["summary"]["drafts"] == 4
    assert report["clean"] is False


def test_stdin_clean_input_exits_zero():
    data = json.dumps([{"id": "one", "text": "The requested edits are ready."}])

    result = run_cli("-", "--format", "json", stdin=data)

    assert result.returncode == 0
    assert json.loads(result.stdout)["clean"] is True


def test_invalid_json_exits_two():
    result = run_cli("-", stdin="not-json")

    assert result.returncode == 2
    assert "invalid input JSON" in result.stderr


def test_missing_input_exits_two():
    result = run_cli()

    assert result.returncode == 2
    assert "provide an input file" in result.stderr
