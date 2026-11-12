# Vietlott UI implementation plan

**Goal:** Match the approved seven-page HTML in native PySide6, preserving all application contracts.
**Spec:** `docs/redesign/HANDOFF.md`, `docs/redesign/vietlott-redesign.html`, and the user's constraints.
**Execution:** Inline, in the supplied directory (not a Git repository). Original UI and protected-file hashes are in `.redesign-work/`.

## Constraints and scope

- Change `app/ui.py`, presentation helpers and new `app/theme.py` / `app/components/` only. No dependencies.
- Preserve every Desktop callback and the widgets/state used by `tests/test_ui.py`.
- No startup requests, retries, storage or computation changes; keep cancellation and worker lifecycle.
- The user explicitly confirmed existing incomplete-backtest-report behavior on 2026-11-10. Incomplete AI suggestions and cancelled history remain unsaved.
- Separate `theme.json` beside config; native Windows titlebar, no animation needed.
- Use the approved icon, recolored SVG icons, painted balls, 236px rail, 56px topline, 34px statusbar, native grids.

## Tasks and validation ledger

- [x] Tokens/QSS, BallLabel and shared components. Assert-based component/render self-check outside immutable tests.
- [x] Shell and overview. Run full existing suite.
- [x] History: searchable source table, balls, download count, empty state. Run full suite.
- [x] Statistics: true windowed data, heatmap/histogram/table/segmented control. Run full suite.
- [x] Odds: exact fractions from existing probabilities, assumption cards. Run full suite.
- [x] Suggestions: controls, ball tickets, explanation and truthful status. Run full suite.
- [x] Verification: existing actions, real report state. Run full suite.
- [x] AI: provider fields, masked/reveal key, streaming and data commitments. Run full suite.
- [x] Theme persistence, two toggles, seven games/pages, 1000x700 and 1920x1080 screenshots, offline/cancel lifecycle, protected hashes, final review.

## Review focus

Small window/DPI must not force horizontal overflow. Empty and unsupported games must not show invented data. Keno's 20 balls and grouped triple results must remain readable. Failed/cancelled workers must restore inputs without fake success. Theme switches must retain entered text/results and must never persist credentials in theme data.

## Baseline

`python -m pytest tests/ -q`: 69 passed, 23 subtests passed. No protected file edited.

## Completion evidence

Each page was followed by the full suite: 69 passed, 23 subtests. Final independent review reran both suites and approved the fixes. See docs/redesign/IMPLEMENTATION.md for validation scope, screenshots, deliberate native differences, and limitations.
