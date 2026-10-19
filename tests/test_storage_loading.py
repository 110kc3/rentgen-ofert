"""Run the actual regional storage resolver against offline fetch fixtures."""
import pathlib
import subprocess


def test_storage_resolution_and_pinning():
    result = subprocess.run(
        ["node", "--test", str(pathlib.Path(__file__).with_name("storage_loading.cjs"))],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
