"""Run offline Node tests of the app's actual loading and retry handlers."""
import pathlib
import subprocess


def test_browser_loading_and_retry_contracts():
    result = subprocess.run(
        ["node", "--test", str(pathlib.Path(__file__).with_name("browser_loading.cjs"))],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
