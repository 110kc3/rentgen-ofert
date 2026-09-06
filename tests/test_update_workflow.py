"""Publication-order contracts for the update workflow."""
import pathlib


ROOT = pathlib.Path(__file__).parents[1]


def test_source_continuity_gate_runs_before_staging_and_force_push():
    workflow = (ROOT / ".github/workflows/update.yml").read_text(
        encoding="utf-8")

    preserve = workflow.index("- name: Preserve previous publication metadata")
    scrape = workflow.index("- name: Scrape listings")
    validate = workflow.index(
        "- name: Validate generated data + source continuity + publish run summary")
    stage = workflow.index("python -m scripts.region_storage stage")
    push = workflow.index("git push --force")

    assert preserve < scrape < validate < stage < push
    assert "allow_source_regression:" in workflow
    assert "--previous-meta" in workflow
    assert "--allow-source-regression" in workflow
    restore = workflow.index('python -m scripts.region_storage restore "$REGION"')
    assert restore < preserve
    assert "no data branch yet — starting fresh" not in workflow


def test_a_rejected_update_cannot_trigger_deploy():
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(
        encoding="utf-8")

    assert "github.event.workflow_run.conclusion == 'success'" in workflow
