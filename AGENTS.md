# Repository instructions

A regional Polish real estate sale listing aggregator and static analysis portal.
Read [TODO.md](TODO.md) and [README.md](README.md) before changing implementation.

## Sources and invariants

- `AGENTS.md` is canonical; `CLAUDE.md` must contain exactly the same bytes. Edit the
  source, reconcile any independent mirror edits, then synchronize in the same change.
- `TODO.md` is the authoritative worklist. Do not treat historical notes as live orders.
- Scraper adapters must respect source continuity and atomic cache replacement.
- Never commit credentials, portal access tokens or production user data.

## Commands

- Runtime: Python 3.11 (`.venv`).
- Test: `.venv/bin/pytest -q`.
- Build / static site: `python3 -m site.build` (or project-specific pipeline).

## Workflow

- Verify exact file paths before editing; preserve unrelated files and formatting.
- Append completed tasks to `TODO.md`'s shipped/completed sections.
