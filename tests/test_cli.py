import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from finops_auditor.cli import main
from finops_auditor.models import AuditSummary


def test_cli_demo_mode_output(capsys):
    code = main(["--demo"])
    assert code == 0
    captured = capsys.readouterr().out
    assert "FinOps Audit" in captured
    assert "ebs_unattached" in captured


def test_cli_demo_mode_json(capsys, tmp_path):
    out_file = tmp_path / "out.json"
    code = main(["--demo", "--format", "json", "--output", str(out_file)])
    assert code == 0
    stdout_json = json.loads(capsys.readouterr().out)
    assert stdout_json["total_findings"] == 4
    file_json = json.loads(out_file.read_text())
    assert file_json == stdout_json


def test_cli_fixture_file(tmp_path, capsys):
    fixture = tmp_path / "test.json"
    fixture.write_text(Path("fixtures/demo.json").read_text())
    code = main(["--fixture", str(fixture)])
    assert code == 0
    assert "FinOps Audit" in capsys.readouterr().out


def test_cli_requires_mode(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_cli_live_mode_calls_scanner(monkeypatch, capsys):
    mock_summary = AuditSummary(
        scanned_at="2026-01-15T00:00:00Z",
        regions=["us-east-1"],
        total_findings=0,
        total_estimated_monthly_savings_usd=0.0,
        unpriced_findings=0,
        findings=[],
    )
    mock_scanner_inst = Mock()
    mock_scanner_inst.run_all.return_value = mock_summary
    mock_scanner_cls = Mock(return_value=mock_scanner_inst)
    monkeypatch.setattr("finops_auditor.cli.AWSFinOpsScanner", mock_scanner_cls)

    code = main(["--live", "--regions", "us-east-1,ap-southeast-1"])
    assert code == 0
    assert "FinOps Audit" in capsys.readouterr().out
    mock_scanner_cls.assert_called_once()


def test_cli_notify_invoked(monkeypatch, capsys):
    mock_notify = Mock()
    monkeypatch.setattr("finops_auditor.cli.notify", mock_notify)
    code = main(["--demo", "--notify", "slack"])
    assert code == 0
    assert mock_notify.call_count == 1
    assert mock_notify.call_args[0][0] == "slack"
