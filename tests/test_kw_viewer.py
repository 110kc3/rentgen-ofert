"""Offline contract checks for private evidence import and address filters."""
import pathlib
import subprocess
import pytest


@pytest.mark.parametrize("filename", ["kw_viewer.cjs", "kw_links.cjs"])
def test_kw_evidence_viewer_contract(filename):
    result = subprocess.run(
        ["node", "--test", str(pathlib.Path(__file__).with_name(filename))],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
