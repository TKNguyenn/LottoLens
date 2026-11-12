# LottoLens Settings — implementation plan

Execution: superpowers:executing-plans, inline with an independent English-catalog task. User requested a settings page, Vietnamese/English and per-game draw counts, plus an About card with only GitHub. User clarified counts mean **draws fetched per action, never deletion/retention**.

Architecture: append page/nav row 7, preserve original rows 0–6 and Desktop API. Presentation-only preferences in `ui_preferences.json` beside config, validated language vi/en and seven per-game counts 1–2000/default100. **Language applies immediately**, as explicitly clarified by the user; Save persists it for future sessions. Retain canonical copy at presentation boundaries rather than reverse-translating display text; skip raw AI/report/input data. Saving sends no request and preserves generated results. Existing history count remains synchronized with the current game's setting. Core, storage, main.py and tests/ immutable.

About card follows supplied reference layout with existing logo/name, honest short product description and one disabled GitHub button until URL is supplied. Do not invent version, author or destination. Retain both gradient themes and compact sidebar behavior.

- [x] Add assert-based settings regression outside immutable tests/, observe failure.
- [x] Implement validated atomic UI preferences and settings/about page, worker input locking, per-game history count sync.
- [x] Add English catalog and translate app-owned labels/buttons/nav/headers/tooltips/help/status. Preserve arbitrary AI/provider text, record payloads and raw report JSON. Verify immediate VI/EN roundtrip and reopen persistence.
- [x] Run full suite and UI checks; native Windows captures/settings layout at 1000/1440/1920 in both themes/languages; independent review; protected hashes.
- [x] Update root implementation_handoff.md, central redesign index and settings README with results/limits.

Results: 69 original tests +23 subtests pass; preferences (offscreen/native), all-game UI, sidebar, gradient and i18n checks pass; native main.py smoke verifies live switch and save with no requests; 22 protected hashes unchanged. Review fixed canonical-source/nested-copy/prize-caption issues and confirmed Ship. See README and root handoff section13 for limits.

Files: app/preferences.py, app/i18n.py, app/ui.py, app/components/__init__.py, app/widgets.py; scripts/check_preferences.py; docs/redesign/settings/ and root handoff. No new dependencies or Git commits (workspace is not a repository).
