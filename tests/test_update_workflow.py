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


def test_hourly_checks_cannot_scrape_early_or_displace_pending_runs():
    workflow = (ROOT / ".github/workflows/update.yml").read_text()
    assert 'cron: "0 6,18 * * *"' in workflow
    assert 'cron: "17 * * * *"' in workflow
    assert "group: rentgen-scrape" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "queue: max" in workflow
    assert "strategy:" not in workflow
    assert workflow.index("python3 -m scripts.schedule_region") < workflow.index("actions/setup-python")
    # Every expensive/publishing step is gated, including post-scrape commands.
    for step in workflow.split("    steps:\n", 1)[1].split("      - ")[3:]:
        assert "if: steps.schedule.outputs.run == 'true'" in step


def test_noop_schedule_cannot_deploy():
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
    assert "needs: publication" in workflow
    assert "if: needs.publication.outputs.published == 'true'" in workflow
    assert 'actions/runs/$SOURCE_RUN/jobs?per_page=100' in workflow
    assert '.conclusion == "success"' in workflow
    assert '.name == "Push refreshed data (single-commit per-region data branch)"' in workflow
    assert workflow.index("  deploy:") < workflow.index("group: rentgen-pages")
