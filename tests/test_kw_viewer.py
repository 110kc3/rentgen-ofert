"""Offline contract checks for private evidence import and address filters."""
import pathlib
import subprocess


def test_kw_evidence_viewer_contract():
    result = subprocess.run(
        ["node", "--test", str(pathlib.Path(__file__).with_name("kw_viewer.cjs"))],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
